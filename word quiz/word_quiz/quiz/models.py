from django.db import models


class Word(models.Model):
    word = models.CharField(max_length=50)
    definition = models.CharField(max_length=255)
    example_sentence = models.CharField(max_length=255)
    example_meaning = models.CharField(max_length=255)
    blanked_sentence = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        # 예문에서 단어를 빈칸으로 변환
        self.blanked_sentence = create_blank_in_sentence(
            self.word, self.example_sentence
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.word


def create_blank_in_sentence(word, sentence):
    """
    주어진 단어를 예문에서 빈칸으로 변환합니다.
    """
    blanked_sentence = sentence.replace(word, "____")
    return blanked_sentence
