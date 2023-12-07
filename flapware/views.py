import logging
import os

import httpx
from django.http import HttpResponseRedirect

from django.shortcuts import render

from flapware.forms import HomeSearchForm, HomeResultsForm
from flapware.helpers import get_home_airports


def save_home(request):
    if request.method == "POST":
        airports = request.POST.getlist("airports")
        home_airports = request.session.get("home_airports", {})
        for airport in airports:
            airport_details = airport.split(",")
            airport_name = airport_details[0]
            airport_iata = airport_details[1]
            if airport_iata not in home_airports:
                home_airports[airport_iata] = airport_name
        request.session["home_airports"] = home_airports
    return HttpResponseRedirect("/")


def home(request):
    home_airports = get_home_airports(request)
    form = HomeSearchForm()
    if request.method == "POST":
        form = HomeSearchForm(request.POST)
        if form.is_valid():
            with httpx.Client() as client:
                try:
                    response = client.post(
                        f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/security/oauth2/token",
                        data={
                            "grant_type": "client_credentials",
                            "client_id": os.environ.get("AMADEUS_API_KEY"),
                            "client_secret": os.environ.get("AMADEUS_API_SECRET"),
                        },
                    )
                    response.raise_for_status()
                    response = response.json()
                    access_token = response["access_token"]
                    token_type = response["token_type"]
                    response = client.get(
                        f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/reference-data/locations",
                        params={
                            "subType": "AIRPORT",
                            "keyword": form.cleaned_data["city_or_airport"],
                        },
                        headers={"Authorization": f"{token_type} {access_token}"},
                    )
                    response.raise_for_status()
                    airports = (
                        (
                            f"{airport['name']},{airport['iataCode']}",
                            f"{airport['name']} ({airport['address']['cityName']}, {airport['address']['countryName']})",
                        )
                        for airport in response.json()["data"]
                        if airport["iataCode"] not in home_airports
                    )
                except httpx.RequestError as exc:
                    logging.error(
                        f"An error occurred while requesting {exc.request.url}."
                    )
                except httpx.HTTPStatusError as exc:
                    logging.error(
                        f"Error response {exc.response.status_code} while requesting {exc.request.url}."
                    )

            return render(
                request,
                "home.html",
                {
                    "form": form,
                    "results_form": HomeResultsForm(choices=airports),
                    "home_airports": home_airports,
                },
            )
    return render(
        request,
        "home.html",
        {
            "form": form,
            "home_airports": home_airports,
        },
    )
