import csv
import sys
import os
import django
import time
import difflib
import random  # 무작위로 섞기 위해 random 모듈 추가
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
import asyncio
from asgiref.sync import sync_to_async

# 현재 스크립트의 상위 디렉토리를 PYTHONPATH에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Django 설정 파일을 환경 변수로 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "STT.settings")

# Django 환경 초기화
django.setup()

from STT.views import chatbot_response  # 챗봇 응답 함수 가져오기


def load_test_data(csv_file_path):
    test_data = []
    with open(csv_file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            expected_value = row.get("Expected Answer", "")

            # 예상 답변을 리스트 형태로 저장
            if expected_value:
                expected_keywords = expected_value.split(
                    ",")  # 예상 답변을 ','로 분리하여 리스트로 변환
            else:
                expected_keywords = []  # 예상 답변이 없을 경우 빈 리스트

            test_data.append({
                "question": row.get("Question", "Unknown question"),
                "expected_keywords": expected_keywords,
            })
    return test_data


# 복합 질문 여부를 확인하는 함수 (예상 답안에 ','가 포함된 경우 복합 질문으로 처리)
def is_complex_question(expected_keywords):
    return len(expected_keywords) > 1


# 예상 키워드가 예측된 강의 제목 리스트 중에 있는지 확인하는 함수
def calculate_accuracy(expected_keywords, predicted_titles, complex_question):
    if complex_question:
        # 복합 질문인 경우: 모든 예상 키워드가 예측된 강의에 있어야 함
        return all(
            any(expected_keyword in title for title in predicted_titles)
            for expected_keyword in expected_keywords)
    else:
        # 복합 질문이 아닌 경우: 하나의 예상 키워드라도 예측된 강의 중에 있으면 맞음
        # 유사도 기반으로 정확도 계산
        return any(
            max(
                difflib.SequenceMatcher(None, expected_keyword, title).ratio()
                for title in predicted_titles) > 0.7
            for expected_keyword in expected_keywords)


async def write_to_csv(file_path, data):
    # CSV 파일 쓰기를 동기적으로 처리
    with open(file_path, mode="w", newline="", encoding="utf-8") as file:
        fieldnames = [
            "Question", "Expected Keyword", "Predicted Title", "Similarity"
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


async def evaluate_chatbot_performance(test_data, output_csv_path):
    true_positive = 0
    false_positive = 0
    false_negative = 0
    correct_predictions = 0  # 정확히 예측한 질문의 수
    total_questions = len(test_data)
    total_response_time = 0  # 총 응답 시간을 저장할 변수
    all_y_true = []
    all_y_pred = []

    # 데이터를 무작위로 섞음
    random.shuffle(test_data)

    results_to_write = []  # CSV에 쓸 데이터를 저장할 리스트

    for data in test_data:
        question = data["question"]
        expected_keywords = set(data["expected_keywords"])  # 예상 키워드

        # 응답 시간 측정 시작
        start_time = time.time()

        # 실제 챗봇 검색 함수 호출 (비동기 호출)
        predicted_lectures = await chatbot_response(question)

        # 응답 시간 측정 종료
        end_time = time.time()
        total_response_time += end_time - start_time  # 응답 시간 누적

        # Lecture 객체인지 확인하고, Lecture 객체일 경우 강의 제목 추출
        predicted = set()
        for lecture in predicted_lectures:
            if hasattr(lecture, "lecture_title"):
                predicted.add(lecture.lecture_title)  # Lecture 객체인 경우 제목 추출
            else:
                predicted.add(lecture)  # Lecture 객체가 아니면 문자열 그대로 추가

        print(f"예상 키워드: {expected_keywords}")
        print(f"예측된 강의 제목: {predicted}")

        # 복합 질문 여부 확인
        complex_question = is_complex_question(expected_keywords)

        # 정확도 계산을 위한 함수 호출
        is_correct = calculate_accuracy(expected_keywords, predicted,
                                        complex_question)

        # 정확하게 예측한 질문 수
        if is_correct:
            correct_predictions += 1
            all_y_true.append(1)
            all_y_pred.append(1)
        else:
            all_y_true.append(1)
            all_y_pred.append(0)

        # 유사도 계산 및 CSV 저장
        for expected_keyword in expected_keywords:
            for predicted_title in predicted:
                similarity = difflib.SequenceMatcher(None, expected_keyword,
                                                     predicted_title).ratio()
                print(
                    f"Saving to CSV: Question: {question}, Expected: {expected_keyword}, Predicted: {predicted_title}, Similarity: {similarity}"
                )
                results_to_write.append({
                    "Question": question,
                    "Expected Keyword": expected_keyword,
                    "Predicted Title": predicted_title,
                    "Similarity": similarity,
                })

    # CSV 파일 쓰기
    await write_to_csv(output_csv_path, results_to_write)

    # 정확도(Accuracy)
    accuracy = correct_predictions / total_questions if total_questions > 0 else 0

    # 정밀도(Precision), 재현율(Recall), F1 스코어 계산
    precision = precision_score(all_y_true,
                                all_y_pred,
                                average="binary",
                                zero_division=0)
    recall = recall_score(all_y_true,
                          all_y_pred,
                          average="binary",
                          zero_division=0)
    f1 = f1_score(all_y_true, all_y_pred, average="binary", zero_division=0)

    # 평균 응답 시간 계산
    average_response_time = (total_response_time /
                             total_questions if total_questions > 0 else 0)

    # 성능 결과 출력
    print(f"정밀도(Precision): {precision:.2f}")
    print(f"재현율(Recall): {recall:.2f}")
    print(f"F1 Score: {f1:.2f}")
    print(f"정확도(Accuracy): {accuracy:.2f}")
    print(f"평균 응답 시간: {average_response_time:.4f} 초")


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(current_dir, "corrected_unique_test_questions.csv")
    output_csv_path = os.path.join(current_dir, "similarity_results.csv")

    test_data = load_test_data(csv_file_path)
    asyncio.run(evaluate_chatbot_performance(test_data, output_csv_path))  # 비동기 실행