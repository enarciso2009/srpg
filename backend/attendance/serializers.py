from rest_framework import serializers
from .models import WorkShift, WorkShiftTracking, WorkShiftLocation, FraudAlert

class WorkShiftSerializer(serializers.ModelSerializer):
    duration = serializers.SerializerMethodField() # opcional, facilita relatorios
    class Meta:
        model = WorkShift
        fields = "__all__"
        read_only_fields = ("start_time", "end_time", "status", "employee")

    def get_duration(self, obj):
        if obj.start_time and obj.end_time:
            return (obj.end_time - obj.start_time).total_seconds() / 3600
        return None

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
    class Meta:
        model = FraudAlert
        fields = ['id', 'user_email', 'fraud_type', 'description', 'created_at', 'resolved']

class WorkShiftStartSerializer(serializers.ModelSerializer):
    device_id = serializers.CharField(write_only=True)
    class Meta:
        model = WorkShift
        fields = ['latitude', 'longitude', 'device_id']