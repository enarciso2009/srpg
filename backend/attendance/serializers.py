from rest_framework import serializers
from .models import WorkShift, WorkShiftTracking, WorkShiftLocation, FraudAlert

class WorkShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkShift
        fields = "__all__"
        read_only_fields = ("start_time", "end_time", "status", "employee")

class WorkShiftTrackingSerializer(serializers. ModelSerializer):
    class Meta:
        model = WorkShiftTracking
        fields = ['id', 'shift', 'latitude', 'longitude', 'timestamp']
        read_only_fields = ['timestamp']

class WorkShiftLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkShiftLocation
        fields = ['latitude', 'longitude']

class FraudAlertSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    class Meta:
        model = FraudAlert
        fields = ['id', 'user_email', 'fraud_type', 'description', 'created_at', 'resolved']

class WorkShiftStartSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkShift
        fields = ['latitude', 'longitude'] # apenas o que vem do app