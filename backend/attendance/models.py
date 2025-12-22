from django.conf import settings
from accounts.models import Employee
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.conf import settings

class WorkShift(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="shifts")
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)

    start_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    start_longitude = models.DecimalField(max_digits=9, decimal_places=6)

    end_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    end_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    create_at = models.DateTimeField(auto_now_add=True)

    @property
    def status(self):
        return "OPEN" if self.end_time is None else "CLOSED"

    def __str__(self):
        return f'{self.employee.user.email} - {self.status}'

class WorkShiftLocation(models.Model):
    work_shift = models.ForeignKey(WorkShift, on_delete=models.CASCADE, related_name="locations")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.work_shift.employee} @ {self.created_at}"


class WorkShiftTracking(models.Model):
    shift = models.ForeignKey('WorkShift', on_delete=models.CASCADE, related_name='trackings')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timestamp = models. DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Tracking of {self.shift.employee.user.email} at {self.timestamp}"

class FraudAlert(models.Model):
    FRAUD_TYPES = (
        ('DEVICE', 'Dispositivo não autorizado'),
        ('LOCATION', 'Localização suspeita'),
        ('TIME', 'Tempo invalido'),
        ('TRACKING', 'Tracking inconsistente'),
        ('MULTI_SHIFT', 'Turno duplicado'),
    )
    FRAUD_POINTS = {
        "MULTI_SHIFT": 30,
        "OUT_OF_RADIUS": 25,
        "SHORT_SHIFT":20,
        "SPEED_IMPOSSIBLE": 40,
        "GPS_INVALID": 15,
    }
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    work_shift = models.ForeignKey(WorkShift, on_delete=models.SET_NULL, null=True, blank=True)
    fraud_type = models.CharField(max_length=20, choices=FRAUD_TYPES)
    severity = models.CharField(max_length=20)
    score = models.PositiveIntegerField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.fraud_type}"
