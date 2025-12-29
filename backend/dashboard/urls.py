from unicodedata import name

from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="dashboard-home"),
    path("fraudes/", views.fraud_dashboard , name="dashboard-fraudes"),
    path("fraud-alerts-json/", views.fraud_alerts_admin_json, name="fraud-alerts-json"),
    path('attendance/workshift-report/', views.workshift_report_view, name='workshift-report'),


]
