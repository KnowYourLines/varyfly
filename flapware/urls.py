from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("add-home", views.add_home, name="add_home"),
    path("remove-home", views.remove_home, name="remove_home"),
]
