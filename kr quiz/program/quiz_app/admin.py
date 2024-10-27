from django.contrib import admin
from .models import QuizResult, Sentence, Stopword

# QuizResult 모델을 관리자 페이지에서 볼 수 있게 등록
admin.site.register(QuizResult)


# Sentence 모델을 Django Admin에서 관리할 수 있게 등록
@admin.register(Sentence)
class SentenceAdmin(admin.ModelAdmin):
    list_display = ("id", "text")  # 관리자가 문장의 ID와 내용을 나란히 볼 수 있게 설정


# Stopword 모델을 Admin에 등록
admin.site.register(Stopword)
