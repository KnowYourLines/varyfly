import logging
import os

import httpx

from django.shortcuts import render

from flapware.forms import HomeForm


async def home(request):
    form = HomeForm()
    if request.method == "POST":
        form = HomeForm(request.POST)
        search_results = []
        if form.is_valid():
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
                        f"https://{os.environ.get('AMADEUS_BASE_URL')}/v1/reference-data/locations",
                        params={
                            "subType": "AIRPORT",
                            "keyword": form.cleaned_data["city_or_airport"],
                        },
                        headers={"Authorization": f"{token_type} {access_token}"},
                    )
                    response.raise_for_status()
                    search_results = response.json()["data"]
                except httpx.RequestError as exc:
                    logging.error(
                        f"An error occurred while requesting {exc.request.url}."
                    )
                except httpx.HTTPStatusError as exc:
                    logging.error(
                        f"Error response {exc.response.status_code} while requesting {exc.request.url}."
                    )

        return render(
            request,
            "home.html",
            {"form": form, "search_results": search_results},
        )
    return render(
        request,
        "home.html",
        {"form": form},
    )
