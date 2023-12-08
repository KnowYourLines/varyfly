from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("save-home", views.save_home, name="save_home"),
    path(
        "cheapest-destinations",
        views.cheapest_destinations,
        name="cheapest_destinations",
    ),
]
