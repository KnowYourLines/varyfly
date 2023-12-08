import os


def get_home_city(request):
    return request.session.get("home_city", {})


def get_saved_destinations(request):
    return request.session.get("saved_destinations", {})


async def get_city_iata_for_airport(client, token_type, access_token, airport_iata):
    response = await client.get(
        f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/reference-data/locations",
        params={
            "subType": "AIRPORT",
            "keyword": airport_iata,
        },
        headers={"Authorization": f"{token_type} {access_token}"},
    )
    response.raise_for_status()
    result = next(
        airport
        for airport in response.json()["data"]
        if airport["iataCode"] == airport_iata
    )

    return result["address"]["cityCode"]
