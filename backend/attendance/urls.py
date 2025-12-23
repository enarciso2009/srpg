from django.urls import path
from .views import (
    StartShiftView,
    EndShiftView,
    ShiftListView,
    ShiftListAllView,
    ShiftFilteredView,
    ShiftReportView,
    ShiftTrackingView,
    FraudAlertListView,
    FraudAlertAdminListView,
    FraudAlertResolveView,
)


urlpatterns = [
    path('start/', StartShiftView.as_view(), name='shift-start'),
    path('end/', EndShiftView.as_view(), name='shift-end'),

    path('myshifts/', ShiftListView.as_view(), name='shift-list-user'),
    path('allshifts/', ShiftListAllView.as_view(), name='shift-list-all'),

    path('filter/', ShiftFilteredView.as_view(), name='shift-filter'),
    path('report/', ShiftReportView.as_view(), name='shift-report'),

    path('tracking/', ShiftTrackingView.as_view(), name='shift-tracking'),

    # 🔔 Fraud alerts
    path('fraud-alerts/', FraudAlertListView.as_view(), name='fraud-alerts'),
    path('fraud-alerts/all/', FraudAlertAdminListView.as_view(), name='fraud-alerts-all'),
    path('fraud-alerts/<int:pk>/resolve/', FraudAlertResolveView.as_view(), name='fraud-resolve'),
]
