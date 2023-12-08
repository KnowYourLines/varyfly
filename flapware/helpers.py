def get_home_city(request):
    return request.session.get("home_city", {})
