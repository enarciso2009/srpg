from django.urls import path
from . import views
from .views import save_signature_api

urlpatterns = [
    path('start/', views.StartShiftView.as_view(), name='shift-start'),
    path('end/', views.EndShiftView.as_view(), name='shift-end'),

    path('workshift/<int:pk>/adjust/', views.AdjustiShiftView.as_view(), name='adjust-shift'),

    path('myshifts/', views.ShiftListView.as_view(), name='shift-list-user'),
    path('allshifts/', views.ShiftListAllView.as_view(), name='shift-list-all'),

    path('filter/', views.ShiftFilteredView.as_view(), name='shift-filter'),


    path('reports/workshift/', views.ShiftReportView.as_view(), name='workshift-report'),
    path('reports/workshift/pdf/', views.workshift_report_pdf_view, name='workshift-report-pdf'),
    path('api/reports/workshift/pdf/', views.workshift_report_pdf_api, name='workshift-report-pdf-api'),
    path('save-signature/', save_signature_api, name='save_signature_api'),

    path('tracking/', views.ShiftTrackingView.as_view(), name='shift-tracking'),
    path('tracking/dashboard/', views.ShiftTrackingDashboardView.as_view()),

    # 🔔 Fraud alerts
    path('fraud-alerts/', views.FraudAlertListView.as_view(), name='fraud-alerts'),
    path('fraud-alerts/all/', views.FraudAlertAdminListView.as_view(), name='fraud-alerts-all'),
    path('fraud-alerts/<int:pk>/resolve/', views.FraudAlertResolveView.as_view(), name='fraud-resolve'),
    path('fraud-admin-json/', views.frauds_admin_list, name='fraud-admin-json'),



]
