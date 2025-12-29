from geopy.distance import geodesic
from attendance.models import FraudAlert
from math import radians, cos, sin, asin, sqrt

def create_fraud_alert(user, work_shift, fraud_type, description):
    FraudAlert.objects.create(
        user=user,
        work_shift=work_shift,
        fraud_type=fraud_type,
        description=description
    )

def distance_km(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).km



def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c
