import asyncio
import logging
import os

import httpx
from asgiref.sync import sync_to_async
from django.http import HttpResponseRedirect

from django.shortcuts import render

from veyfly.forms import HomeSearchForm, HomeResultsForm
from veyfly.helpers import (
    get_home_city,
    get_destination_cities_for_airport,
    access_token_and_type,
)


async def save_home(request):
    if request.method == "POST":
        city = request.POST.get("city")
        city_details = city.split(",")
        city_name = city_details[0]
        city_iata = city_details[1]
        city_country_code = city_details[2]
        city_latitude = city_details[3]
        city_longitude = city_details[4]
        city_country_name = city_details[5]
        async with httpx.AsyncClient() as client:
            try:
                token_type, access_token = await access_token_and_type(client)
                response = await client.get(
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


async def cheapest_flight_dates(request):
    destination_iata = request.GET.get("destination")
    home_city = await sync_to_async(get_home_city)(request)
    origin_iata = home_city["iata"]
    async with httpx.AsyncClient() as client:
        try:
            token_type, access_token = await access_token_and_type(client)
            response = await client.get(
                f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/shopping/flight-dates",
                params={
                    "origin": origin_iata,
                    "destination": destination_iata,
                    "duration": 15,
                    "nonStop": True,
                    "departureDate": "2023-12-15,2024-03-11",
                },
                headers={"Authorization": f"{token_type} {access_token}"},
            )
            response.raise_for_status()
            logging.info(response.json())
            logging.info(len(response.json()["data"]))
            flight_dates = response.json().get("data", [])
        except httpx.RequestError as exc:
            logging.error(f"An error occurred while requesting {exc.request.url}.")
        except httpx.HTTPStatusError as exc:
            logging.error(
                f"Error response {exc.response.status_code} while requesting {exc.request.url}: {exc.response.text}"
            )
    return render(
        request,
        "cheapest_flight_dates.html",
        {
            "flight_dates": flight_dates,
            "destination_city": request.GET.get("city"),
            "destination_country": request.GET.get("country"),
        },
    )


async def safety(request):
    async with httpx.AsyncClient() as client:
        try:
            token_type, access_token = await access_token_and_type(client)
            full_city_name = (
                request.GET.get("city_name", "").replace("/", " ").split(" ")
            )
            city_name = full_city_name[0]
            for word in full_city_name[1:]:
                if len(city_name + " " + word) > 10:
                    break
                city_name += " " + word
            if city_name == "MARRAKECH":
                city_name = "MARRAKESH"
            elif city_name == "MALTA":
                city_name = "VALLETTA"
            elif city_name == "MALE":
                city_name = "MALÉ"
            response = await client.get(
                f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/reference-data/locations/cities",
                params={
                    "keyword": city_name,
                    "countryCode": request.GET.get("country_code"),
                    "max": 1,
                },
                headers={"Authorization": f"{token_type} {access_token}"},
            )
            response.raise_for_status()
            city_data = response.json().get("data")
            if city_data:
                city = city_data[0]
                if not city.get("geoCode"):
                    city = {
                        "geoCode": {
                            "latitude": float(request.GET.get("latitude")),
                            "longitude": float(request.GET.get("longitude")),
                        }
                    }
            else:
                city = {
                    "geoCode": {
                        "latitude": float(request.GET.get("latitude")),
                        "longitude": float(request.GET.get("longitude")),
                    }
                }
            response = await client.get(
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
                response = await client.get(
                    links.get("next"),
                    headers={"Authorization": f"{token_type} {access_token}"},
                )
                areas = areas + response.json().get("data", [])
                links = response.json().get("meta", {}).get("links", {})
            areas = [
                area
                for area in areas
                if city_name.upper() in area["name"].upper()
                or "MARRAKECH" in area["name"].upper()
            ]
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
            token_type, access_token = await access_token_and_type(client)
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
            added_cities = {home_city["iata"]}
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


async def home(request):
    home_city = await sync_to_async(get_home_city)(request)
    form = HomeSearchForm()
    if request.method == "POST":
        form = HomeSearchForm(request.POST)
        if form.is_valid():
            async with httpx.AsyncClient() as client:
                try:
                    token_type, access_token = await access_token_and_type(client)
                    response = await client.get(
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
