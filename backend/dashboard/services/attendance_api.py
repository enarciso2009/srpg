import requests
from django.conf import settings


def get_api_base():
    return settings.API_BASE_URL

def get_active_shifts(token):
    url = f"{get_api_base()}/attendance/shifts/active/",
    return requests.get(url).json()


def get_open_frauds(token):
    url = f"{get_api_base()}/attendance/frauds/open/",
    return requests.get(url).json()
