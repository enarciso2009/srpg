from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView)
from drf_spectacular.views import (SpectacularAPIView, SpectacularSwaggerView)


urlpatterns = [
    path("admin/", admin.site.urls),

    # API schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # Swagger UI
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # API's
    path("api/auth/", include("accounts.urls")),
    path("api/attendance/", include("attendance.urls")),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("api/accounts/", include("accounts.urls")),

    # Dashboard
    path("dashboard/", include("dashboard.urls")),

    # Accounts
    path("accounts/", include("django.contrib.auth.urls")),


]
