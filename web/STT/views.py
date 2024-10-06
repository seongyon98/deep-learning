import difflib
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Q
from .models import Lecture, Keyword
from konlpy.tag import Okt
import pytz
from .stopwords import STOP_WORDS, JOSA, PUNCTUATION, COMPOUND_NOUNS
import time
import re
import openai
import os
from django.core.cache import cache
import asyncio
import hashlib
from asgiref.sync import sync_to_async  # 비동기 DB 호출을 위한 import
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

okt = Okt()

os.environ["OPENAI_API_KEY"] = "YOUR_OPENAPI_KEY"
openai.api_key = os.getenv("OPENAI_API_KEY")

# 캐시 키를 저장할 set (중복 방지)
cached_keys = set()


def generate_cache_key(question):
    return hashlib.md5(question.encode("utf-8")).hexdigest()


def find_similar_question(question):
    # 모든 캐시된 질문을 리스트로 변환
    cached_questions = list(cached_keys)

    if not cached_questions:
        return None

    # 입력 질문과 캐시된 질문들을 함께 벡터화
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([question] + cached_questions)

    # 첫 번째 벡터는 입력된 질문, 나머지는 캐시된 질문들
    input_question_vector = vectors[0]
    cached_question_vectors = vectors[1:]

    # 코사인 유사도 계산 (입력 질문과 모든 캐시된 질문들 간의 유사도)
    similarities = cosine_similarity(
        input_question_vector, cached_question_vectors
    ).flatten()

    # 유사도가 가장 높은 질문의 인덱스와 그 유사도를 찾음
    max_similarity_index = similarities.argmax()
    max_similarity = similarities[max_similarity_index]

    # 유사도가 0.7 이상인 경우 해당 캐시된 질문의 결과 반환
    if max_similarity > 0.7:
        similar_question = cached_questions[max_similarity_index]
        return cache.get(similar_question)

    # 유사한 질문이 없으면 None 반환
    return None


async def fetch_openai_response(question):
    try:
        print("openai api 호출")
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 대한민국 초등학교 4학년 수학 용어를 전문적으로 교정하는 도우미입니다. "
                        "제공된 용어에서 모든 철자 및 오타를 최대한 정확하게 교정하세요. "
                        "오타나 철자 오류가 있는 용어도 최대한 추론하여 올바른 용어로 수정하세요. "
                        "그 후, 교정된 용어 중 초등학교 4학년 수학 교과서에 나오는 핵심 용어만 추출해 주세요. "
                        "일반적인 단어는 제외하고, 수학과 직접적으로 관련된 용어만 포함하세요. "
                        "추가적인 단어를 포함하지 말고, 교정된 용어만 출력하세요."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"질문의 오타를 모두 교정한 후, 초등학교 4학년 수학과 관련된 올바른 용어만 추출해 주세요. "
                        f"추가적인 단어를 포함하지 말고, 교정된 질문에 등장하는 정확한 키워드만 추출하세요. "
                        f"교정된 키워드만 출력해주세요. 질문은: {question} 입니다."
                    ),
                },
            ],
            temperature=0,
            top_p=0,
        )
        return response["choices"][0]["message"]["content"].strip()
    except openai.error.OpenAIError as e:
        print(f"OpenAI 호출 오류: {e}")
        return "오류가 발생했습니다. 다시 시도해 주세요."
    except Exception as e:
        print(f"일반 오류: {e}")
        return "오류가 발생했습니다."


async def correct_question_with_openai(question):
    cache_key = generate_cache_key(question)

    # 캐시에서 유사한 질문 찾기
    cached_response = find_similar_question(question)
    if cached_response:
        return cached_response

    await asyncio.sleep(0.1)  # 비동기 대기

    corrected_response = await fetch_openai_response(question)

    # 교정된 질문과 키워드 부분을 분리
    if "\n" in corrected_response:
        corrected_question, keywords_part = corrected_response.split("\n", 1)
    else:
        corrected_question = corrected_response
        keywords_part = "키워드 없음"  # 키워드가 없는 경우 기본 메시지

    print(f"OpenAI 교정된 질문: {corrected_question}")
    print(f"추출된 키워드: {keywords_part.strip()}")

    # 캐시에 결과 저장 (예: 1시간 동안 캐시)
    cache.set(cache_key, corrected_response, timeout=3600)
    cached_keys.add(cache_key)  # 캐시 키를 set에 추가
    return corrected_response


def extract_nouns_and_adjectives_korean(question):
    start_time = time.time()

    found_compounds = []
    for compound in COMPOUND_NOUNS:
        if compound in question:
            found_compounds.append(compound)

    tokens = okt.pos(question, norm=True, stem=True)
    keywords = [word for word, pos in tokens if pos in ["Noun", "Adjective"]]

    filtered_keywords = [
        keyword
        for keyword in keywords
        if keyword not in STOP_WORDS
        and keyword not in JOSA
        and keyword not in PUNCTUATION
    ]

    if found_compounds:
        filtered_keywords.extend(found_compounds)

    unique_keywords = list(set(filtered_keywords))
    unique_keywords = [keyword.replace(" ", "") for keyword in unique_keywords]

    end_time = time.time()
    print(f"실행 시간: {end_time - start_time} 초")

    return unique_keywords


@sync_to_async  # 비동기 DB 호출을 위한 데코레이터
def get_lecture_data(keywords):
    keyword_objects = Keyword.objects.filter(keyword__in=keywords)
    lectures = Lecture.objects.filter(keywords__in=keyword_objects).distinct()
    print(f"검색된 강의 수: {lectures.count()}")
    return lectures


@sync_to_async  # 비동기 DB 호출을 위한 데코레이터
def lecture_exists(lecture_queryset):
    return lecture_queryset.exists()


async def chatbot_response(question):
    start_time = time.time()

    # 형태소 분석 및 강의 검색을 한 번만 수행
    keyword_kor = extract_nouns_and_adjectives_korean(question)
    results = await get_lecture_data(keyword_kor)

    if not await lecture_exists(results):  # 강의가 없을 경우 OpenAI 호출
        print("검색된 강의 수가 0개입니다. OpenAI 호출을 시작합니다...")
        corrected_question = await correct_question_with_openai(question)
        keyword_kor = extract_nouns_and_adjectives_korean(corrected_question)
        results = await get_lecture_data(keyword_kor)

        if not await lecture_exists(results):  # 여전히 강의가 없으면 종료
            return ["죄송합니다. 강의를 찾지 못했습니다."]

    end_time = time.time()
    print(f"chatbot_response 실행 시간: {end_time - start_time} 초")

    return await sync_to_async(list)(results)  # 비동기적으로 리스트로 변환


def qa_process(request):
    results = None
    chat_history = request.session.get("chat_history", [])
    show_cards = False

    if request.method == "POST":
        question = request.POST.get("question_input")
        print(f"질문: {question}")
        results = asyncio.run(chatbot_response(question))

        kst = pytz.timezone("Asia/Seoul")
        current_time = timezone.now().astimezone(kst).strftime("%Y-%m-%d %H:%M:%S")

        if results and isinstance(results[0], Lecture):
            show_cards = True
            answer_str = ", ".join([result.lecture_title for result in results])
        else:
            answer_str = results[0]

        chat_history.append(
            {
                "question": question,
                "answer": answer_str,
                "timestamp": current_time,
            }
        )
        request.session["chat_history"] = chat_history

    keywords = [
        "큰 수",
        "곱셈",
        "사각형",
        "꺾은선그래프",
        "소수",
        "분수",
        "다각형",
        "평면도형",
        "막대그래프",
        "각도",
        "규칙 찾기",
        "삼각형",
        "나눗셈",
    ]

    context = {
        "results": results,
        "chat_history": chat_history,
        "show_cards": show_cards,
        "keywords": keywords,
    }

    return render(request, "qa_template.html", context)


def clear_history(request):
    request.session.pop("chat_history", None)
    return redirect("qa_process")
