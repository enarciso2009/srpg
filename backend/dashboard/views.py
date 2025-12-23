from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .services.attendance_api import (get_open_frauds, get_active_shifts)


def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required

def dashboard_home(request):
    # Turnos abertos
    token = request.session.get("access_token")

    context = {
        "active_shifts": [],
        "open_frauds": [],
    }

    if token:
        try:
            context['active_shifts'] = get_active_shifts(token)
            context["open_frauds"] = get_open_frauds(token)
        except Exception as e:
            context["api_error"] = str(e)
    return render(request, "dashboard/home.html", context)

