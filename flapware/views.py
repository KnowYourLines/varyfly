from django.http import HttpResponseRedirect
from django.shortcuts import render

from flapware.forms import HomeForm


async def home(request):
    form = HomeForm()
    if request.method == "POST":
        form = HomeForm(request.POST)
        if form.is_valid():
            return render(
                request,
                "home.html",
                {"form": form},
            )
    return render(
        request,
        "home.html",
        {"form": form},
    )
