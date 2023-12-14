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


async def access_token_and_type(client):
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


async def get_city_details(
    city_iata,
    country_code,
    client,
    token_type,
    access_token,
):
    response = await client.get(
        f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/reference-data/locations",
        params={
            "keyword": city_iata,
            "countryCode": country_code,
            "subType": "CITY",
        },
        headers={"Authorization": f"{token_type} {access_token}"},
    )
    response.raise_for_status()
    city_data = response.json().get("data", [])
    city = next(city for city in city_data if city["iataCode"] == city_iata)
    return city
