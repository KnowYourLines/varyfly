from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("save-home/", views.save_home, name="save_home"),
    path(
        "destinations/",
        views.destinations,
        name="destinations",
    ),
    path(
        "safety/",
        views.safety,
        name="safety",
    ),
]
