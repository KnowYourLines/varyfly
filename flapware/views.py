import asyncio
import logging
import os

import httpx
from asgiref.sync import sync_to_async
from django.http import HttpResponseRedirect

from django.shortcuts import render

from flapware.forms import HomeSearchForm, HomeResultsForm
from flapware.helpers import (
    get_home_city,
    get_destination_cities_for_airport,
)


def save_home(request):
    if request.method == "POST":
        city = request.POST.get("city")
        city_details = city.split(",")
        city_name = city_details[0]
        city_iata = city_details[1]
        city_country_code = city_details[2]
        city_latitude = city_details[3]
        city_longitude = city_details[4]
        city_country_name = city_details[5]
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
                        "keyword": city_name,
                        "countryCode": city_country_code,
                    },
                    headers={"Authorization": f"{token_type} {access_token}"},
                )
                response.raise_for_status()
                airports = [
                    airport["iataCode"]
                    for airport in response.json().get("data", [])
                    if airport["address"]["cityCode"] == city_iata
                ]
            except httpx.RequestError as exc:
                logging.error(f"An error occurred while requesting {exc.request.url}.")
            except httpx.HTTPStatusError as exc:
                logging.error(
                    f"Error response {exc.response.status_code} while requesting {exc.request.url}."
                )
        home_city = {
            "iata": city_iata,
            "name": city_name,
            "country_code": city_country_code,
            "latitude": city_latitude,
            "longitude": city_longitude,
            "country_name": city_country_name,
            "airports": airports,
        }
        request.session["home_city"] = home_city
    return HttpResponseRedirect("/")


def add_cities(request):
    if request.method == "POST":
        cities = request.POST.getlist("cities")
        destinations = request.session.get("saved_destinations", {})
        for city in cities:
            city_details = city.split(",")
            city_name = city_details[0]
            city_iata = city_details[1]
            city_latitude = city_details[2]
            city_longitude = city_details[3]
            if city_iata not in destinations:
                destinations[city_iata] = {
                    "name": city_name,
                    "latitude": city_latitude,
                    "longitude": city_longitude,
                }
        request.session["saved_destinations"] = destinations
    return HttpResponseRedirect("/destinations/")


def remove_cities(request):
    if request.method == "POST":
        cities = request.POST.getlist("cities")
        saved_destinations = request.session.get("saved_destinations", {})
        for city in cities:
            city_details = city.split(",")
            iata = city_details[0]
            if iata in saved_destinations:
                del saved_destinations[iata]
        request.session["saved_destinations"] = saved_destinations
    return HttpResponseRedirect("/destinations/")


async def sights(request):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
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
            response = await client.get(
                f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/location/analytics/category-rated-areas",
                params={
                    "latitude": float(request.GET.get("latitude")),
                    "longitude": float(request.GET.get("longitude")),
                },
                headers={"Authorization": f"{token_type} {access_token}"},
            )
            response.raise_for_status()
            sight_scores = next(
                scores["categoryScores"]["sight"]
                for scores in response.json()["data"]
                if scores["radius"] == 1500
            )
            response = await client.get(
                f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/reference-data/locations/pois",
                params={
                    "latitude": float(request.GET.get("latitude")),
                    "longitude": float(request.GET.get("longitude")),
                    "radius": 20,
                    "page[limit]": 10000,
                    "categories": "SIGHTS",
                },
                headers={"Authorization": f"{token_type} {access_token}"},
            )
            response.raise_for_status()
            pois = response.json().get("data", [])
            links = response.json().get("meta", {}).get("links", {})
            while links.get("next"):
                response = await client.get(
                    links.get("next"),
                    headers={"Authorization": f"{token_type} {access_token}"},
                )
                pois = pois + response.json().get("data", [])
                links = response.json().get("meta", {}).get("links", {})
        except httpx.RequestError as exc:
            logging.error(f"An error occurred while requesting {exc.request.url}.")
        except httpx.HTTPStatusError as exc:
            logging.error(
                f"Error response {exc.response.status_code} while requesting {exc.request.url}."
            )
    return render(
        request,
        "sights.html",
        {"sights": pois, "scores": sight_scores},
    )


async def nightlife(request):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
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
            response = await client.get(
                f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/location/analytics/category-rated-areas",
                params={
                    "latitude": float(request.GET.get("latitude")),
                    "longitude": float(request.GET.get("longitude")),
                },
                headers={"Authorization": f"{token_type} {access_token}"},
            )
            response.raise_for_status()
            scores = next(
                scores["categoryScores"]["nightLife"]
                for scores in response.json()["data"]
                if scores["radius"] == 1500
            )
            response = await client.get(
                f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/reference-data/locations/pois",
                params={
                    "latitude": float(request.GET.get("latitude")),
                    "longitude": float(request.GET.get("longitude")),
                    "radius": 20,
                    "page[limit]": 10000,
                    "categories": "NIGHTLIFE",
                },
                headers={"Authorization": f"{token_type} {access_token}"},
            )
            response.raise_for_status()
            pois = response.json().get("data", [])
            links = response.json().get("meta", {}).get("links", {})
            while links.get("next"):
                response = await client.get(
                    links.get("next"),
                    headers={"Authorization": f"{token_type} {access_token}"},
                )
                pois = pois + response.json().get("data", [])
                links = response.json().get("meta", {}).get("links", {})
        except httpx.RequestError as exc:
            logging.error(f"An error occurred while requesting {exc.request.url}.")
        except httpx.HTTPStatusError as exc:
            logging.error(
                f"Error response {exc.response.status_code} while requesting {exc.request.url}."
            )
    return render(
        request,
        "nightlife.html",
        {"pois": pois, "scores": scores},
    )


def safety(request):
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
                f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/reference-data/locations/cities",
                params={
                    "keyword": request.GET.get("city_name"),
                    "countryCode": request.GET.get("country_code"),
                    "max": 1,
                },
                headers={"Authorization": f"{token_type} {access_token}"},
            )
            response.raise_for_status()
            city = response.json()["data"][0]
            response = client.get(
                f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/safety/safety-rated-locations",
                params={
                    "latitude": city["geoCode"]["latitude"],
                    "longitude": city["geoCode"]["longitude"],
                    "radius": 20,
                    "page[limit]": 10000,
                },
                headers={"Authorization": f"{token_type} {access_token}"},
            )
            response.raise_for_status()
            areas = response.json().get("data", [])
            links = response.json().get("meta", {}).get("links", {})
            while links.get("next"):
                response = client.get(
                    links.get("next"),
                    headers={"Authorization": f"{token_type} {access_token}"},
                )
                areas = areas + response.json().get("data", [])
                links = response.json().get("meta", {}).get("links", {})
        except httpx.RequestError as exc:
            logging.error(f"An error occurred while requesting {exc.request.url}.")
        except httpx.HTTPStatusError as exc:
            logging.error(
                f"Error response {exc.response.status_code} while requesting {exc.request.url}."
            )
    return render(
        request,
        "safety.html",
        {"areas": areas},
    )


async def destinations(request):
    home_city = await sync_to_async(get_home_city)(request)
    if not home_city:
        return render(
            request,
            "no_home_saved.html",
        )
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
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
            tasks = []
            for iata in home_city["airports"]:
                tasks.append(
                    asyncio.ensure_future(
                        get_destination_cities_for_airport(
                            client, token_type, access_token, iata
                        )
                    )
                )

            destinations_for_home_airports = await asyncio.gather(*tasks)
            cities = []
            added_cities = set()
            for airport_destinations in destinations_for_home_airports:
                for city in airport_destinations:
                    if city["iataCode"] not in added_cities:
                        added_cities.add(city["iataCode"])
                        cities.append(city)
        except httpx.RequestError as exc:
            logging.error(f"An error occurred while requesting {exc.request.url}.")
        except httpx.HTTPStatusError as exc:
            logging.error(
                f"Error response {exc.response.status_code} while requesting {exc.request.url}."
            )
        return render(
            request,
            "destinations.html",
            {"cities": cities},
        )


def home(request):
    home_city = get_home_city(request)
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
                            "subType": "CITY",
                            "keyword": form.cleaned_data["city"],
                        },
                        headers={"Authorization": f"{token_type} {access_token}"},
                    )
                    response.raise_for_status()
                    cities = [
                        (
                            f"{city['address']['cityName']},{city['iataCode']},{city['address']['countryCode']},"
                            f"{city['geoCode']['latitude']},{city['geoCode']['longitude']},"
                            f"{city['address']['countryName']}",
                            f"{city['address']['cityName']}, {city['address']['countryName']}",
                        )
                        for city in response.json().get("data", [])
                        if city["iataCode"] != home_city.get("iata")
                    ]
                except httpx.RequestError as exc:
                    logging.error(
                        f"An error occurred while requesting {exc.request.url}."
                    )
                except httpx.HTTPStatusError as exc:
                    logging.error(
                        f"Error response {exc.response.status_code} while requesting {exc.request.url}."
                    )
            results_form = HomeResultsForm(choices=cities) if cities else None
            return render(
                request,
                "home.html",
                {
                    "form": form,
                    "results_form": results_form,
                    "home_city": home_city,
                },
            )
    return render(
        request,
        "home.html",
        {
            "form": form,
            "home_city": home_city,
        },
    )
