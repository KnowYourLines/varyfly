import logging
import os

import httpx


def get_home_city(request):
    return request.session.get("home_city", {})


async def get_destination_cities_for_airport(
    client, token_type, access_token, airport_iata
):
    response = await client.get(
        f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/airport/direct-destinations",
        params={
            "departureAirportCode": airport_iata,
        },
        headers={"Authorization": f"{token_type} {access_token}"},
    )
    response.raise_for_status()
    return response.json().get("data", [])


async def async_access_token_and_type(client):
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
    return token_type, access_token


def access_token_and_type(client):
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
    return token_type, access_token


async def get_city(client, token_type, access_token, request):
    full_city_name = request.GET.get("city_name", "").split(" ")
    city_name = full_city_name[0]
    for word in full_city_name[1:]:
        if len(city_name + " " + word) > 10:
            break
        city_name += " " + word
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
    city = response.json()["data"][0]
    return city, city_name


async def get_category_scores(category, city, client, token_type, access_token):
    response = await client.get(
        f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/location/analytics/category-rated-areas",
        params={
            "latitude": city["geoCode"]["latitude"],
            "longitude": city["geoCode"]["longitude"],
        },
        headers={"Authorization": f"{token_type} {access_token}"},
    )
    response.raise_for_status()
    category_scores = next(
        scores["categoryScores"][category]
        for scores in response.json()["data"]
        if scores["radius"] == 1500
    )
    return category_scores


async def get_pois(category, city, city_name, client, token_type, access_token):
    response = await client.get(
        f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/reference-data/locations/pois",
        params={
            "latitude": city["geoCode"]["latitude"],
            "longitude": city["geoCode"]["longitude"],
            "radius": 20 if city_name != "HELSINKI" else 12,
            "page[limit]": 10000,
            "categories": category,
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
    return pois


async def pois_and_scores(poi_category, score_category, request):
    async with httpx.AsyncClient() as client:
        try:
            token_type, access_token = await async_access_token_and_type(client)
            city, city_name = await get_city(client, token_type, access_token, request)
            scores = await get_category_scores(
                score_category, city, client, token_type, access_token
            )
            pois = await get_pois(
                poi_category, city, city_name, client, token_type, access_token
            )
        except httpx.RequestError as exc:
            logging.error(f"An error occurred while requesting {exc.request.url}.")
        except httpx.HTTPStatusError as exc:
            logging.error(
                f"Error response {exc.response.status_code} while requesting {exc.request.url}: {exc.response.text}"
            )
    return pois, scores
