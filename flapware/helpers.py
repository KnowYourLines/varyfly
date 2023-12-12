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
