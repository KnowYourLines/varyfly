def get_home_airports(request):
    return request.session.get("home_airports", {})
