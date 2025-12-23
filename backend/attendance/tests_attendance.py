from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from accounts.models import User, Employee, UserDevice
from .models import WorkShift, WorkShiftLocation, FraudAlert
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


class AttendanceAPITestCase(APITestCase):
    def setUp(self):
        # ----------------------
        # Usuário normal
        # ----------------------
        self.user = User.objects.create_user(
            username="user1",
            email="user1@test.com",
            password="pass1234"
        )
        self.employee = Employee.objects.create(
            user=self.user,
            matricula="EMP01",
            base_latitude=Decimal("10.0"),
            base_longitude=Decimal("10.0")
        )
        self.device = UserDevice.objects.create(
            user=self.user,
            device_id="DEVICE123"
        )

        # ----------------------
        # Usuário Admin
        # ----------------------
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="adminpass"
        )
        self.admin_employee = Employee.objects.create(
            user=self.admin_user,
            matricula="ADM01",
            base_latitude=Decimal("20.0"),
            base_longitude=Decimal("20.0")
        )
        self.admin_device = UserDevice.objects.create(
            user=self.admin_user,
            device_id="ADMINDEVICE"
        )

        # ----------------------
        # Client normal
        # ----------------------
        self.client = APIClient()
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "user1@test.com", "password": "pass1234"}
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        # ----------------------
        # Client admin
        # ----------------------
        self.admin_client = APIClient()
        admin_token_response = self.admin_client.post(
            reverse("token_obtain_pair"),
            {"email": "admin@test.com", "password": "adminpass"}
        )
        self.admin_token = admin_token_response.data["access"]
        self.admin_client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")

    # ----------------------
    # Testes Start Shift
    # ----------------------
    def test_start_shift_without_device(self):
        url = reverse("shift-start")
        data = {"latitude": 10.0, "longitude": 10.0}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_start_shift_success(self):
        url = reverse("shift-start")
        data = {"device_id": "DEVICE123", "latitude": 10.0, "longitude": 10.0}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue("id" in response.data)

    # ----------------------
    # Testes End Shift
    # ----------------------
    def test_end_shift_success(self):
        shift = WorkShift.objects.create(
            employee=self.employee,
            start_latitude=10,
            start_longitude=10,
            start_time=timezone.now() - timedelta(minutes=10)
        )
        url = reverse("shift-end")
        data = {"device_id": "DEVICE123", "latitude": 10, "longitude": 10}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        shift.refresh_from_db()
        self.assertIsNotNone(shift.end_time)

    def test_end_shift_too_early(self):
        shift = WorkShift.objects.create(
            employee=self.employee,
            start_latitude=10,
            start_longitude=10,
            start_time=timezone.now()
        )
        url = reverse("shift-end")
        data = {"device_id": "DEVICE123", "latitude": 10, "longitude": 10}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ----------------------
    # Testes Shift List
    # ----------------------
    def test_shift_list_user(self):
        WorkShift.objects.create(
            employee=self.employee,
            start_latitude=10,
            start_longitude=10,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now()
        )
        url = reverse("shift-list-user")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    def test_shift_list_all_admin_only(self):
        url = reverse("shift-list-all")
        # Usuário normal não pode acessar
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Admin acessa
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ----------------------
    # Testes Shift Filter
    # ----------------------
    def test_shift_filter_by_date_and_status(self):
        shift1 = WorkShift.objects.create(
            employee=self.employee,
            start_latitude=10,
            start_longitude=10,
            start_time=timezone.now() - timedelta(days=2),
            end_time=timezone.now() - timedelta(days=1)
        )
        shift2 = WorkShift.objects.create(
            employee=self.employee,
            start_latitude=10,
            start_longitude=10,
            start_time=timezone.now() - timedelta(days=1)  # aberto
        )
        url = reverse("shift-filter")
        response = self.client.get(url, {
            "start_date": (timezone.now() - timedelta(days=3)).date(),
            "end_date": (timezone.now() - timedelta(days=1)).date(),
            "status": "closed"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], shift1.id)

    # ----------------------
    # Testes Shift Report
    # ----------------------
    def test_shift_report_admin_only(self):
        WorkShift.objects.create(
            employee=self.employee,
            start_latitude=10,
            start_longitude=10,
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now()
        )
        url = reverse("shift-report")
        # Usuário normal não pode acessar
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Admin acessa
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    # ----------------------
    # Testes Shift Tracking
    # ----------------------
    def test_shift_tracking_success(self):
        shift = WorkShift.objects.create(
            employee=self.employee,
            start_latitude=10,
            start_longitude=10,
            start_time=timezone.now() - timedelta(minutes=10)
        )
        url = reverse("shift-tracking")
        data = {"device_id": "DEVICE123", "latitude": 10, "longitude": 10}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_shift_tracking_too_soon(self):
        shift = WorkShift.objects.create(
            employee=self.employee,
            start_latitude=10,
            start_longitude=10,
            start_time=timezone.now() - timedelta(minutes=10)
        )
        WorkShiftLocation.objects.create(work_shift=shift, latitude=10, longitude=10)
        url = reverse("shift-tracking")
        data = {"device_id": "DEVICE123", "latitude": 10, "longitude": 10}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_shift_tracking_invalid_gps(self):
        shift = WorkShift.objects.create(
            employee=self.employee,
            start_latitude=10,
            start_longitude=10,
            start_time=timezone.now() - timedelta(minutes=10)
        )
        url = reverse("shift-tracking")
        data = {"device_id": "DEVICE123", "latitude": 0, "longitude": 0}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ----------------------
    # Testes Fraud Alerts
    # ----------------------
    def test_fraud_alert_user_and_admin_views(self):
        alert1 = FraudAlert.objects.create(user=self.user, fraud_type="DEVICE", description="Test Alert", severity="LOW", score=10)
        alert2 = FraudAlert.objects.create(user=self.admin_user, fraud_type="DEVICE", description="Admin Alert", severity="LOW", score=10)

        # Usuário normal só vê seus alerts
        url_user = reverse("fraud-alerts")
        response = self.client.get(url_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], alert1.id)

        # Admin vê todos
        url_admin = reverse("fraud-alerts-all")
        response = self.admin_client.get(url_admin)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 2)

    def test_fraud_alert_resolve(self):
        alert = FraudAlert.objects.create(user=self.user, fraud_type="DEVICE", description="To Resolve", severity="LOW", score=10)
        url = reverse("fraud-resolve", kwargs={"pk": alert.id})

        # Usuário normal não pode resolver
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Admin resolve
        response = self.admin_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        alert.refresh_from_db()
        self.assertTrue(alert.resolved)
