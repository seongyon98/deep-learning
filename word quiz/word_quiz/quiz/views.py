from django.shortcuts import render, redirect
from .models import Word
from sentence_transformers import SentenceTransformer, util
import random

model = SentenceTransformer("jhgan/ko-sroberta-multitask")


def start_view(request):
    return render(request, "quiz/start.html")  # start.html 템플릿을 반환


def quiz_view(request):
    current_question = request.session.get("current_question", 0)

    # 처음 세션 초기화
    if "quiz_words" not in request.session:
        all_words = list(Word.objects.all())
        if len(all_words) < 10:
            return render(
                request,
                "quiz/no_data.html",
                {
                    "message": "단어 데이터가 충분하지 않습니다. 최소 10개의 단어가 필요합니다."
                },
            )

        # 10개의 랜덤 단어 선택
        request.session["quiz_words"] = random.sample(
            [word.id for word in all_words], 10
        )
        request.session["hint_count"] = 0

    # 10문제를 모두 풀면 결과 페이지로 이동
    if current_question >= 10:
        request.session["current_question"] = 0
        return render(
            request, "quiz/complete.html", {"message": "퀴즈를 완료했습니다!"}
        )

    word_id = request.session["quiz_words"][current_question]
    word = Word.objects.get(id=word_id)
    hint_count = request.session.get("hint_count", 0)

    if request.method == "POST":
        user_input = request.POST.get("answer")

        # 유사도 계산
        word_embedding = model.encode([word.word], convert_to_tensor=True)
        user_embedding = model.encode([user_input], convert_to_tensor=True)
        cosine_score = util.pytorch_cos_sim(user_embedding, word_embedding).item()

        if cosine_score >= 0.95:
            result = f"✅ 정답입니다! 유사도: {cosine_score:.2f}"
            request.session["current_question"] = current_question + 1
            request.session["hint_count"] = 0
            return render(request, "quiz/result.html", {"result": result, "next": True})
        else:
            hint_count += 1
            request.session["hint_count"] = hint_count

            # 힌트를 제공하는 로직
            if hint_count == 1:
                hint = word.word[0]  # 첫 글자 힌트 제공
                result = f"❌ 틀렸습니다. 첫 번째 힌트: '{hint}', 유사도: {cosine_score:.2f}. 다시 풀어보세요!"
            elif hint_count == 2:
                hint = word.word[:2]  # 첫 두 글자 힌트 제공
                result = f"❌ 틀렸습니다. 두 번째 힌트: '{hint}', 유사도: {cosine_score:.2f}. 다시 풀어보세요!"
            elif hint_count == 3:
                hint = word.word[:3]  # 세 번째 힌트 제공
                result = f"❌ 틀렸습니다. 세 번째 힌트: '{hint}', 유사도: {cosine_score:.2f}. 다시 풀어보세요!"
            else:
                result = f"❌ 틀렸습니다. 정답은 '{word.word}'입니다. 유사도: {cosine_score:.2f}."
                request.session["current_question"] = current_question + 1
                request.session["hint_count"] = 0
                return render(
                    request, "quiz/result.html", {"result": result, "next": True}
                )

        return render(
            request,
            "quiz/quiz.html",
            {"word": word, "result": result, "current_question": current_question + 1},
        )

    question_type = random.choice(["dfn", "ex"])
    if question_type == "dfn":
        question = {"type": "definition", "content": word.definition}
    else:
        question = {"type": "example", "content": word.blanked_sentence}

    return render(
        request,
        "quiz/quiz.html",
        {"word": word, "question": question, "current_question": current_question + 1},
    )


def complete_view(request):
    return render(request, "quiz/complete.html", {"message": "퀴즈를 완료했습니다!"})


def no_data_view(request):
    return render(
        request,
        "quiz/no_data.html",
        {"message": "단어 데이터가 충분하지 않습니다. 최소 10개의 단어가 필요합니다."},
    )
