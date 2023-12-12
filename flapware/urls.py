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
    path("add-cities/", views.add_cities, name="add_cities"),
    path("remove-cities/", views.remove_cities, name="remove_cities"),
    path(
        "safety/<str:username>/",
        views.safety,
        name="safety",
    ),
]
