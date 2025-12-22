from geopy.distance import geodesic
from attendance.models import FraudAlert

def create_fraud_alert(user, work_shift, fraud_type, description):
    FraudAlert.objects.create(
        user=user,
        work_shift=work_shift,
        fraud_type=fraud_type,
        description=description
    )

def distance_km(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).km
