import os


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
