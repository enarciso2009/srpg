from rest_framework import serializers
from .models import WorkShift, WorkShiftTracking, WorkShiftLocation, FraudAlert

class WorkShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkShift
        fields = "__all__"
        read_only_fields = ("start_time", "end_time", "status", "employee")


class WorkShiftTrackingSerializer(serializers. ModelSerializer):
    device_id = serializers.CharField(write_only=True)
    class Meta:
        model = WorkShiftTracking
        fields = ['shift', 'latitude', 'longitude', 'device_id', 'timestamp']
        read_only_fields = ['timestamp']

class WorkShiftLocationSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = WorkShiftLocation
        fields = ['latitude', 'longitude', 'timestamp']

class FraudAlertSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    employee_name = serializers.CharField(
        source='user.get_full_name',
        read_only=True
    )

    employee_matricula = serializers.CharField(
        source='work_shift.employee.matricula',
        read_only=True
    )
    shift_id = serializers.IntegerField(source='work_shift.id', read_only=True)

    class Meta:
        model = FraudAlert
        fields = ['id', 'employee_id', 'employee_name','matricula', 'user_email', 'shift_id', 'fraud_type', 'severity',
                  'score', 'description', 'created_at', 'resolved', 'created_at', 'shift_id',]

class WorkShiftStartSerializer(serializers.ModelSerializer):
    device_id = serializers.CharField(write_only=True)
    class Meta:
        model = WorkShift
        fields = ['latitude', 'longitude', 'device_id']

class FraudAlertListSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(
        source="work_shift.employee.user.get_full_name",
        read_only=True
    )
    matricula = serializers.CharField(
        source="work_shift.employee.matricula",
        read_only=True
    )

    class Meta:
        model = FraudAlert
        fields = ['id', 'employee_name', 'matricula', 'fraud_type', 'severity', 'score', 'description', 'created_at', 'resolved',]


class FraudAlertAdminSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(
        source="work_shift.employee.user.get_full_name",
        read_only=True
    )
    employee_email = serializers.EmailField(
        source="work_shift.employee.user.email",
        read_only=True
    )
    employee_matricula = serializers.CharField(
        source="work_shift.employee.matricula",
        read_only=True
    )
    shift_id = serializers.IntegerField(
        source="work_shift.id",
        read_only=True
    )

    class Meta:
        model = FraudAlert
        fields = [
            'id',
            'employee_name',
            'employee_email',
            'employee_matricula',
            'shift_id',
            'fraud_type',
            'severity',
            'score',
            'description',
            'created_at',
            'resolved',
        ]
