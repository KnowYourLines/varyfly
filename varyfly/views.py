import asyncio
import logging
import os
from datetime import datetime
from operator import itemgetter

import httpx
from asgiref.sync import sync_to_async
from django.http import HttpResponseRedirect
from django.shortcuts import render

from varyfly.forms import HomeSearchForm, HomeResultsForm, TravelPreferencesForm
from varyfly.helpers import (
    get_home_city,
    get_destination_cities_for_airport,
    access_token_and_type,
    get_city_details,
    save_travel_preferences,
    get_travel_preferences,
    add_precise_city_lat_long,
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
    destination_iata = request.GET.get("destination_iata")
    country_code = request.GET.get("country_code")
    saved_travel_preferences = await sync_to_async(get_travel_preferences)(request)
    if saved_travel_preferences:
        form = TravelPreferencesForm(initial=saved_travel_preferences)
    else:
        form = TravelPreferencesForm()
    if request.method == "POST":
        form = TravelPreferencesForm(request.POST)
        if form.is_valid():
            await sync_to_async(save_travel_preferences)(request, form.cleaned_data)
            home_city = await sync_to_async(get_home_city)(request)
            origin_iata = home_city["iata"]
            async with httpx.AsyncClient() as client:
                try:
                    token_type, access_token = await access_token_and_type(client)
                    city = await get_city_details(
                        destination_iata, country_code, client, token_type, access_token
                    )
                    params = {
                        "origin": origin_iata,
                        "destination": destination_iata,
                        "nonStop": form.cleaned_data["nonstop_only"],
                    }
                    if form.cleaned_data["trip_length"] in [
                        f"{i}" for i in range(1, 16)
                    ]:
                        params["duration"] = form.cleaned_data["trip_length"]
                    else:
                        params["oneWay"] = True
                    response = await client.get(
                        f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/shopping/flight-dates",
                        params=params,
                        headers={"Authorization": f"{token_type} {access_token}"},
                    )
                    response.raise_for_status()
                    response = response.json()
                    flights = response.get("data", [])
                    currency = response.get("meta", {}).get("currency")
                    airports = response["dictionaries"]["locations"]
                    for flight in flights:
                        flight[
                            "readable_origin"
                        ] = f"{airports[flight['origin']]['detailedName']} ({flight['origin']})"
                        flight[
                            "readable_destination"
                        ] = f"{airports[flight['destination']]['detailedName']} ({flight['destination']})"
                        departure_date = datetime.strptime(
                            flight["departureDate"], "%Y-%m-%d"
                        )
                        flight["readable_departure"] = departure_date.strftime(
                            "%a %d %b %Y"
                        )
                        flight["offers_querystring"] = flight["links"][
                            "flightOffers"
                        ].split("?")[1]
                        if flight.get("returnDate"):
                            return_date = datetime.strptime(
                                flight["returnDate"], "%Y-%m-%d"
                            )
                            flight["readable_return"] = return_date.strftime(
                                "%a %d %b %Y"
                            )
                except httpx.RequestError as exc:
                    logging.error(
                        f"An error occurred while requesting {exc.request.url}."
                    )
                    return render(
                        request,
                        "no_flight_dates_found.html",
                        {
                            "form": form,
                            "destination_city": city["name"],
                            "destination_country": city["address"]["countryName"],
                        },
                    )
                except httpx.HTTPStatusError as exc:
                    logging.error(
                        f"Error response {exc.response.status_code} while requesting {exc.request.url}: {exc.response.text}"
                    )
                    return render(
                        request,
                        "no_flight_dates_found.html",
                        {
                            "form": form,
                            "destination_city": city["name"],
                            "destination_country": city["address"]["countryName"],
                        },
                    )
            return render(
                request,
                "cheapest_flight_dates.html"
                if flights
                else "no_flight_dates_found.html",
                {
                    "flights": flights,
                    "destination_city": city["name"],
                    "destination_country": city["address"]["countryName"],
                    "currency": currency,
                    "form": form,
                },
            )

    async with httpx.AsyncClient() as client:
        try:
            token_type, access_token = await access_token_and_type(client)
            city = await get_city_details(
                destination_iata, country_code, client, token_type, access_token
            )
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
            "form": form,
            "destination_city": city["name"],
            "destination_country": city["address"]["countryName"],
        },
    )


async def safety(request):
    async with httpx.AsyncClient() as client:
        try:
            token_type, access_token = await access_token_and_type(client)
            city_iata = request.GET.get("city_iata")
            country_code = request.GET.get("country_code")
            city = await get_city_details(
                city_iata, country_code, client, token_type, access_token
            )
            city = await add_precise_city_lat_long(
                city, country_code, client, token_type, access_token
            )
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
            city_areas_not_matching_city_names = [
                "MARRAKESH",
                "MALÉ",
                "VALLETTA",
                "MINNEAPOLIS",
                "CASTRIES",
                "MANAMA",
                "KOLN",
                "LEIPZIG",
                "TEL AVIV",
                "KLAIPEDA",
            ]
            areas = [
                area
                for area in areas
                if city["name"].upper() in area["name"].upper()
                or any(
                    name in area["name"].upper()
                    for name in city_areas_not_matching_city_names
                )
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
        {
            "areas": areas,
            "destination_city": city["name"],
            "destination_country": city["address"]["countryName"],
        },
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
        cities = sorted(
            cities,
            key=lambda destination_city: destination_city["address"]["countryName"],
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
