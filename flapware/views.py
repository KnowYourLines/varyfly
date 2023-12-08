import asyncio
import logging
import os

import httpx
from asgiref.sync import sync_to_async
from django.http import HttpResponseRedirect

from django.shortcuts import render

from flapware.forms import HomeSearchForm, HomeResultsForm
from flapware.helpers import get_home_city, get_city_iata_for_airport


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
        home_city = {
            "iata": city_iata,
            "name": city_name,
            "country_code": city_country_code,
            "latitude": city_latitude,
            "longitude": city_longitude,
            "country_name": city_country_name,
        }
        request.session["home_city"] = home_city
    return HttpResponseRedirect("/")


async def recommend_destinations(request):
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
            response = await client.get(
                f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/shopping/flight-destinations",
                params={
                    "origin": home_city["iata"],
                },
                headers={"Authorization": f"{token_type} {access_token}"},
            )
            response.raise_for_status()
            destination_airports = [
                flight["destination"] for flight in response.json()["data"]
            ]
            tasks = []
            for iata in destination_airports:
                tasks.append(
                    asyncio.ensure_future(
                        get_city_iata_for_airport(
                            client, token_type, access_token, iata
                        )
                    )
                )

            cheap_city_iatas = await asyncio.gather(*tasks)
            logging.info(cheap_city_iatas)
        except httpx.RequestError as exc:
            logging.error(f"An error occurred while requesting {exc.request.url}.")
        except httpx.HTTPStatusError as exc:
            logging.error(exc.response.text)
            logging.error(
                f"Error response {exc.response.status_code} while requesting {exc.request.url}."
            )
    return render(
        request,
        "recommend_destinations.html",
        {},
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
                        for city in response.json()["data"]
                        if city["iataCode"] != home_city["iata"]
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
