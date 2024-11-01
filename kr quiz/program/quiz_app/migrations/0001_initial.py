# Generated by Django 4.2.16 on 2024-09-25 04:48

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="QuizResult",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("user_answer", models.CharField(max_length=255)),
                ("correct_answer", models.CharField(max_length=255)),
                ("is_correct", models.BooleanField()),
                ("question_sentence", models.TextField()),
                ("question_word", models.CharField(max_length=255)),
                ("time_taken", models.FloatField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Sentence",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("text", models.TextField()),
                ("added_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
