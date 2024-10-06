from django.apps import AppConfig


class SttConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "STT"

    def ready(self):
        from .views import extract_nouns_and_adjectives_korean  # 함수 임포트

        print("서버 시작 시 extract_nouns_and_adjectives_korean 실행")
        test_question = "서버 실행합니다."  # 테스트 질문
        keywords = extract_nouns_and_adjectives_korean(test_question)
        print(f"추출된 키워드: {keywords}")
