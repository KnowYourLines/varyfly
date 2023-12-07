from django.shortcuts import render

from flapware.forms import HomeForm


def home(request):
    form = HomeForm()
    return render(
        request,
        "home.html",
        {"form": form},
    )
