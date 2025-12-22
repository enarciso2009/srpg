from django.urls import path

from .views import EndShiftView, ShiftListAllView, ShiftListView, StartShiftView, ShiftTrackingView, FraudAlertListView

from django.urls import path
from .views import (
    StartShiftView, EndShiftView,
    ShiftListView, ShiftListAllView,
    ShiftFilteredView, ShiftReportView,
    ShiftTrackingView, ShiftTrackingView
)

urlpatterns = [
    path('start/', StartShiftView.as_view(), name='shift-start'),
    path('end/', EndShiftView.as_view(), name='shift-end'),
    path('myshifts/', ShiftListView.as_view(), name='shift-list-user'),
    path('allshifts/', ShiftListAllView.as_view(), name='shift-list-all'),
    path('filter/', ShiftFilteredView.as_view(), name='shift-filter'),
    path('report/', ShiftReportView.as_view(), name='shift-report'),
    path('track/', ShiftTrackingView.as_view(), name='shift-track' ),
    path('tracking/', ShiftTrackingView.as_view(), name='shift-tracking'),
    path('track/', ShiftTrackingView.as_view(), name='shift-track'),
    path('frauds/', FraudAlertListView.as_view(), name='fraud-alerts'),
    path('fraud-alerts/', FraudAlertListView.as_view()),
    path('fraud-alerts/all/', FraudAlertListView.as_view()),
    path('fraud-alerts/<int:pk>/resolve/', FraudAlertListView.as_view()),

]
