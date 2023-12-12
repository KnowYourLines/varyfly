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


async def get_location_scores_for_city(client, token_type, access_token, city):
    response = await client.get(
        f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/location/analytics/category-rated-areas",
        params={
            "latitude": city["geoCode"]["latitude"],
            "longitude": city["geoCode"]["longitude"],
        },
        headers={"Authorization": f"{token_type} {access_token}"},
    )
    response.raise_for_status()
    city_scores = next(
        score["categoryScores"]
        for score in response.json().get("data", [])
        if score["radius"] == 1500
    )
    city["location_scores"] = city_scores
    return city
