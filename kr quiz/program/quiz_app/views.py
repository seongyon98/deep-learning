from django.shortcuts import render, redirect
from konlpy.tag import Kkma
import random, time
from .models import QuizResult, Sentence, Stopword
import re  # 정규 표현식 모듈 추가


kkma = Kkma()

# 품사 태그 매핑
pos_map = {
    "NNG": "명사",
    "NNP": "명사",
    "NNB": "명사",
    "NP": "대명사",
    "NR": "수사",
    "VV": "동사",
    "VA": "형용사",
    "MAG": "부사",
    "MM": "관형사",
    "JKS": "조사",
    "JKC": "조사",
    "JKG": "조사",
    "JKO": "조사",
    "JKB": "조사",
    "JKV": "조사",
    "JX": "조사",
    "JC": "조사",
}


# index 함수 추가
def index(request):
    return render(request, "index.html")


def load_sentences():
    # 데이터베이스에서 문장만 로드
    db_sentences = list(Sentence.objects.values_list("text", flat=True))
    return db_sentences


def generate_problem(sentences):
    stopwords = list(Stopword.objects.values_list("word", flat=True))
    if sentences:
        # 숫자가 포함되지 않은 문장을 선택할 때까지 반복
        sentence = None
        while sentence is None:
            random_sentence = random.choice(sentences)  # 랜덤한 문장을 선택
            if not re.search(
                r"\d", random_sentence
            ):  # 문장에 숫자가 포함되어 있지 않으면 선택
                sentence = random_sentence

        words = kkma.pos(sentence)  # 형태소 분석
        filtered_words = [
            (word, tag)
            for word, tag in words
            if tag in pos_map and word not in stopwords
        ]

        if filtered_words:
            word, tag = random.choice(filtered_words)  # 랜덤한 단어 선택
            human_readable_tag = pos_map.get(tag, tag)
            return sentence, word, human_readable_tag

    return None, None, None  # 문장이나 단어가 없을 경우 처리


def quiz(request):
    if request.method == "POST":
        # 세션 완전히 초기화
        request.session.flush()  # 기존 세션 값 모두 삭제

        # 새 세션 초기화 (이전 문제 기록 삭제)
        request.session["start_time"] = time.time()
        request.session["score"] = 0
        request.session["problems"] = 1
        request.session["recent_quiz_ids"] = []  # 이전 퀴즈 결과 초기화
        request.session["next_problem"] = False  # 다음 문제 플래그 초기화

        return redirect("problem")
    return render(request, "index.html")


# 문제 풀이 함수
def problem(request):
    sentences = load_sentences()
    if not sentences:
        return render(
            request, "error.html", {"message": "문장 데이터를 불러올 수 없습니다."}
        )

    # 세션에서 문제 번호 및 점수 정보를 가져옴 (없으면 기본값 1과 0 설정)
    problems_solved = request.session.get("problems", 1)
    score = request.session.get("score", 0)

    # POST 요청일 때 (정답 제출 후 처리)
    if request.method == "POST":
        # 사용자가 제출한 답을 처리
        user_answer = request.POST.get("answer", "").strip()
        correct_answer = request.POST.get("correct_answer", "").strip()
        is_correct = user_answer == correct_answer

        # 문제에서 사용된 문장과 단어를 POST로 전달받음
        sentence = request.POST.get("sentence")
        word = request.POST.get("word")

        # 결과 저장
        quiz_result = QuizResult.objects.create(
            user_answer=user_answer,
            correct_answer=correct_answer,
            is_correct=is_correct,
            question_sentence=sentence,  # 문장을 저장
            question_word=word,  # 단어를 저장
            time_taken=time.time() - request.session.get("start_time", time.time()),
        )

        # 최근 퀴즈 결과를 세션에 저장
        recent_quiz_ids = request.session.get("recent_quiz_ids", [])
        recent_quiz_ids.append(quiz_result.id)
        request.session["recent_quiz_ids"] = recent_quiz_ids

        # 정답 여부에 따른 처리
        if is_correct:
            score += 1
            request.session["score"] = score
            result_message = f"정답입니다!"
        else:
            result_message = f"틀렸습니다! '{word}'의 품사는 '{correct_answer}'입니다."

        context = {
            "result_message": result_message,
            "show_next_button": True,  # 다음 문제로 넘어가는 버튼
            "show_results_button": False,
            "problems_solved": problems_solved,  # 문제 번호 유지 (여기서 증가하지 않음)
        }

        # 마지막 문제인 경우 결과 보기 버튼 표시
        if problems_solved >= 10:
            context["show_results_button"] = True
            context["show_next_button"] = (
                False  # 마지막 문제일 경우 다음 문제 버튼 숨김
            )

        # 다음 문제로 넘어갈 수 있도록 플래그 설정
        request.session["next_problem"] = True

        return render(request, "quiz.html", context)

    # GET 요청일 때 (다음 문제로 넘어가는 요청)
    elif request.method == "GET":
        # 다음 문제로 넘어갈 때만 문제 번호를 증가시킴
        if request.session.get("next_problem", False):
            problems_solved += 1
            request.session["problems"] = problems_solved
            request.session["next_problem"] = False  # 문제를 넘길 때마다 리셋

        # 10문제를 모두 풀었으면 결과 페이지로 리다이렉트
        if problems_solved > 10:
            return redirect("results")

        # 새로운 문제를 출제함
        sentence, word, correct_tag = generate_problem(sentences)

        # 세션에 문장과 단어를 저장하여 POST 요청 시 사용할 수 있게 함
        request.session["sentence"] = sentence
        request.session["word"] = word

        context = {
            "sentence": sentence,
            "word": word,
            "correct_tag": correct_tag,
            "result_message": None,
            "show_next_button": False,
            "show_results_button": False,
            "problems_solved": problems_solved,  # 문제 번호 표시
        }

        return render(request, "quiz.html", context)


# 결과 페이지
def results(request):
    # 현재 세션에 저장된 퀴즈 결과만 가져오기 (세션이 종료되면 데이터가 사라짐)
    quiz_results = QuizResult.objects.filter(
        id__in=request.session.get("recent_quiz_ids", [])
    )  # 세션에서 최근 문제의 id를 가져옴

    score = request.session.get("score", 0)
    total_time = time.time() - request.session.get("start_time")

    return render(
        request,
        "results.html",
        {
            "score": score,
            "total_time": total_time,
            "quiz_results": quiz_results,  # 세션에 저장된 문제들만 표시
        },
    )
