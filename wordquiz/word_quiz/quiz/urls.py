from django.urls import path
from .views import start_view, quiz_view, complete_view, no_data_view

urlpatterns = [
    path("", start_view, name="start"),
    path("quiz/", quiz_view, name="quiz"),
    path("complete/", complete_view, name="complete"),
    path("no-data/", no_data_view, name="no_data"),
]
