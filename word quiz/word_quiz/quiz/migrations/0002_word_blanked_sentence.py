# Generated by Django 4.2.16 on 2024-10-11 04:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="word",
            name="blanked_sentence",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]