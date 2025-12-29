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
    ShiftTrackingDashboardView, frauds_admin_list, AdjustiShiftView
)


urlpatterns = [
    path('start/', StartShiftView.as_view(), name='shift-start'),
    path('end/', EndShiftView.as_view(), name='shift-end'),

    path('workshift/<int:pk>/adjust/', AdjustiShiftView.as_view(), name='adjust-shift'),

    path('myshifts/', ShiftListView.as_view(), name='shift-list-user'),
    path('allshifts/', ShiftListAllView.as_view(), name='shift-list-all'),

    path('filter/', ShiftFilteredView.as_view(), name='shift-filter'),
    path('reports/workshift/', ShiftReportView.as_view(), name='workshift-report'),

    path('tracking/', ShiftTrackingView.as_view(), name='shift-tracking'),
    path('tracking/dashboard/', ShiftTrackingDashboardView.as_view()),

    # 🔔 Fraud alerts
    path('fraud-alerts/', FraudAlertListView.as_view(), name='fraud-alerts'),
    path('fraud-alerts/all/', FraudAlertAdminListView.as_view(), name='fraud-alerts-all'),
    path('fraud-alerts/<int:pk>/resolve/', FraudAlertResolveView.as_view(), name='fraud-resolve'),
    path('fraud-admin-json/', frauds_admin_list, name='fraud-admin-json'),

]
