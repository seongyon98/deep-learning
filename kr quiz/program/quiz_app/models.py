from django.db import models


class Sentence(models.Model):
    text = models.TextField()  # 문장 데이터
    added_at = models.DateTimeField(auto_now_add=True)  # 추가된 날짜

    def __str__(self):
        return self.text


class Stopword(models.Model):
    word = models.CharField(max_length=100)  # 제외할 단어 저장
    added_at = models.DateTimeField(auto_now_add=True)  # 추가된 시간

    def __str__(self):
        return self.word


class QuizResult(models.Model):
    user_answer = models.CharField(max_length=255)  # 사용자가 입력한 답
    correct_answer = models.CharField(max_length=255)  # 정답
    is_correct = models.BooleanField()  # 정답 여부
    question_sentence = models.TextField()  # 출제된 문장
    question_word = models.CharField(max_length=255)  # 문제로 출제된 어절
    time_taken = models.FloatField()  # 문제 푸는 데 걸린 시간
    created_at = models.DateTimeField(auto_now_add=True)  # 문제 푼 시간

    def __str__(self):
        return f"문제: {self.question_sentence}, 정답 여부: {self.is_correct}"
