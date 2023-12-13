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
    async_access_token_and_type,
    access_token_and_type,
    pois_and_scores,
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
                token_type, access_token = access_token_and_type(client)
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
                    f"Error response {exc.response.status_code} while requesting {exc.request.url}: {exc.response.text}"
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
    (
        pois,
        sight_scores,
    ) = await pois_and_scores("SIGHTS", "sight", request)
    return render(
        request,
        "sights.html",
        {"sights": pois, "scores": sight_scores},
    )


async def shopping(request):
    (
        pois,
        scores,
    ) = await pois_and_scores("SHOPPING", "shopping", request)
    return render(
        request,
        "shopping.html",
        {"pois": pois, "scores": scores},
    )


async def restaurants(request):
    (
        pois,
        scores,
    ) = await pois_and_scores("RESTAURANT", "restaurant", request)
    return render(
        request,
        "restaurants.html",
        {"pois": pois, "scores": scores},
    )


async def nightlife(request):
    (
        pois,
        scores,
    ) = await pois_and_scores("NIGHTLIFE", "nightLife", request)
    return render(
        request,
        "nightlife.html",
        {"pois": pois, "scores": scores},
    )


def safety(request):
    with httpx.Client() as client:
        try:
            token_type, access_token = access_token_and_type(client)
            full_city_name = request.GET.get("city_name", "").split(" ")
            city_name = full_city_name[0]
            for word in full_city_name[1:]:
                if len(city_name + " " + word) > 10:
                    break
                city_name += " " + word
            response = client.get(
                f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/reference-data/locations/cities",
                params={
                    "keyword": city_name,
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
                f"Error response {exc.response.status_code} while requesting {exc.request.url}: {exc.response.text}"
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
            token_type, access_token = await async_access_token_and_type(client)
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
                f"Error response {exc.response.status_code} while requesting {exc.request.url}: {exc.response.text}"
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
                    token_type, access_token = access_token_and_type(client)
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
                        f"Error response {exc.response.status_code} while requesting {exc.request.url}: {exc.response.text}"
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
