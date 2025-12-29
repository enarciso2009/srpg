# attendance/services/workshift_service.py

from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

# Modelos
from attendance.models import WorkShift, WorkShiftLocation, FraudAlert
from accounts.models import Employee, UserDevice

# Utils
from attendance.utils.antifraud import distance_km, haversine


def parse_coordinate(value):
    """Converte valor para Decimal ou retorna None se inválido"""
    try:
        return Decimal(value)
    except (TypeError, ValueError):
        return None


def validate_shift_location(lat1, lon1, lat2, lon2, max_distance_m=200):
    """Valida se a distância entre dois pontos está dentro do limite"""
    distance = haversine(lat1, lon1, lat2, lon2) * 1000  # metros
    if distance > max_distance_m:
        raise PermissionDenied(f"Fora do raio permitido ({int(distance)}m)")


def validate_user_device(user, device_id):
    """Valida se o usuário está usando um dispositivo registrado"""
    try:
        device = UserDevice.objects.get(user=user)
    except UserDevice.DoesNotExist:
        raise PermissionDenied("Dispositivo não registrado")
    if device.device_id != device_id:
        raise PermissionDenied("Dispositivo não autorizado")


def create_fraud_alert(user, fraud_type, description, work_shift=None):
    """Cria um alerta de fraude baseado no tipo e score"""
    points = FraudAlert.FRAUD_POINTS.get(fraud_type, 10)
    severity = (
        "LOW" if points <= 15 else
        "MEDIUM" if points <= 30 else
        "HIGH"
    )
    FraudAlert.objects.create(
        user=user,
        work_shift=work_shift,
        fraud_type=fraud_type,
        severity=severity,
        score=points,
        description=description
    )


def start_shift(user, latitude, longitude):
    """Inicia um turno para um funcionário"""
    try:
        employee = user.employee
        if not employee.ativo:
            create_fraud_alert(
                user,
                "DEVICE",
                "Tentativa de iniciar turno como empregado inativo"
            )
            raise PermissionDenied("Empregado inativo. Contate o administrador.")
    except Employee.DoesNotExist:
        raise PermissionDenied("Funcionário não encontrado")

    if WorkShift.objects.filter(employee=employee, end_time__isnull=True).exists():
        create_fraud_alert(user, "MULTI_SHIFT", "Tentativa de abrir dois turnos simultâneos")
        raise PermissionDenied("Já existe um turno aberto")

    lat = parse_coordinate(latitude)
    lon = parse_coordinate(longitude)
    if lat is None or lon is None:
        raise PermissionDenied("Latitude e Longitude válidas são obrigatórias")

    last_shift = WorkShift.objects.filter(employee=employee, end_time__isnull=False).order_by("-end_time").first()
    if last_shift:
        dist = distance_km(last_shift.end_latitude, last_shift.end_longitude, lat, lon)
        if dist > 1:
            create_fraud_alert(
                user=user,
                work_shift=None,
                fraud_type="LOCATION",
                description=f"Start a {dist:.2f}km do último End"
            )

    shift = WorkShift.objects.create(
        employee=employee,
        start_latitude=lat,
        start_longitude=lon,
        start_time=timezone.now()
    )
    return shift


def end_shift(user, latitude, longitude):
    """Encerra o turno ativo do funcionário"""
    try:
        employee = user.employee
    except Employee.DoesNotExist:
        raise PermissionDenied("Nenhum turno aberto encontrado")

    try:
        shift = WorkShift.objects.get(employee=employee, end_time__isnull=True)
    except WorkShift.DoesNotExist:
        raise PermissionDenied("Nenhum turno aberto encontrado")

    lat = parse_coordinate(latitude)
    lon = parse_coordinate(longitude)
    if lat is None or lon is None:
        raise PermissionDenied("Latitude e Longitude válidas são obrigatórias")

    # Tempo mínimo de turno (para teste, pode reduzir se quiser)
    min_duration = timedelta(minutes=5)
    if timezone.now() - shift.start_time < min_duration:
        create_fraud_alert(user, "TIME", "Tentativa de encerrar turno antes do tempo mínimo", shift)
        raise PermissionDenied("Tempo mínimo de turno não atingido")

    # Validar distância do início do turno
    validate_shift_location(float(shift.start_latitude), float(shift.start_longitude), float(lat), float(lon))

    now = timezone.now()

    shift.end_latitude = lat
    shift.end_longitude = lon
    shift.end_time = now
    # Aqui entra a duração (regra de negócio)
    shift.diration = now - shift.start_time

    shift.save()
    return shift


def track_location(user, latitude, longitude):
    """Registra a localização do usuário em tempo real"""
    try:
        employee = user.employee
        work_shift = WorkShift.objects.get(employee=employee, end_time__isnull=True)
    except (Employee.DoesNotExist, WorkShift.DoesNotExist):
        raise PermissionDenied("Nenhum turno aberto")

    lat = parse_coordinate(latitude)
    lon = parse_coordinate(longitude)
    if not lat or not lon:
        create_fraud_alert(user, "TRACKING", "GPS inválido (0,0)", work_shift)
        raise PermissionDenied("Localização inválida")

    last_location = WorkShiftLocation.objects.filter(work_shift=work_shift).order_by("-created_at").first()
    if last_location:
        delta = timezone.now() - last_location.created_at
        if delta < timedelta(seconds=60):
            create_fraud_alert(user, "TRACKING", "Envio excessivo de localização", work_shift)
            raise PermissionDenied("Aguarde antes de enviar nova localização")
        distance = haversine(float(last_location.latitude), float(last_location.longitude), float(lat), float(lon))
        hours = delta.total_seconds() / 3600
        if hours > 0 and distance / hours > 150:
            create_fraud_alert(user, "TRACKING", f"Velocidade irreal detectada: {int(distance / hours)} km/h", work_shift)
            raise PermissionDenied("Movimentação irreal detectada")

    WorkShiftLocation.objects.create(
        work_shift=work_shift,
        latitude=lat,
        longitude=lon
    )
    return True

def adjust_shift_end(
        *,
        shift_id,
        adjusted_end_time,
        reason,
        admin_user):
    """
    Ajusta manualmente o encerramento de uma jornada esquecida
    """
    # Segurança
    if not admin_user.is_staff:
        raise PermissionDenied("Apenas administradores podem ajustar jornadas")

    try:
        shift = WorkShift.objects.get(id=shift_id)
    except WorkShift.DoesNotExist:
        raise PermissionDenied("Jornada não encontrada")

    # Não ajustar jornada já encerrada normalmente

    if shift.end_time is not None and shift.adjusted_end_time is None:
        raise PermissionDenied("Esta jornada já foi encerrada corretamente")

    # Validação de tempo

    if adjusted_end_time <= shift.start_time:
        raise PermissionDenied("Hora final deve ser maior que a hora inicial")

    # Proteção contra jornada absurda
    max_duration = timedelta(hours=16)
    if adjusted_end_time - shift.start_time > max_duration:
        raise PermissionDenied("Duração da jornada excede o limite permitido")

    # Aplicar ajuste

    shift.adjusted_end_time = adjusted_end_time
    shift.adjustment_reason = reason
    shift.adjusted_by = admin_user
    shift.adjusted_at = timezone.now()

    shift.save(
        update_fields=[
            "adjusted_end_time",
            "adjusted_reason",
            "adjusted_by",
            "adjusted_at"
        ]
    )
    return shift

def minutes_to_hhmm(minutes):
    if minutes is None:
        return None

    sign = "-" if minutes < 0 else ""
    minutes = abs(minutes)

    hours = minutes // 60
    mins = minutes % 60

    return f"{sign}{hours:02d}:{mins:02d}"

STANDARD_SHIFT_MINUTES = 8 * 60 #480

def calculate_shift_mietrics(shift):
    """
    Retorna métricas da jornada:
    - duração
    - atrasos
    - hora extra
    """

    duration_minutes = shift.get_duration_minutes()

    #Jornada aberta
    if duration_minutes is None:
        return {
            "duration_minutes": None,
            "delay_minutes": None,
            "extra_minutes": None,
        }

    diff = duration_minutes - STANDARD_SHIFT_MINUTES

    delay = abs(diff) if diff < 0 else 0
    extra = diff if diff > 0 else 0

    return {
        "duration_minutes": duration_minutes,
        "delay_minutes": delay,
        "extra_minutes": extra,
    }

def build_shift_report_row(shift):
    metrics = calculate_shift_mietrics(shift)
    return {
        "employee": shift.employee.user.email,
        "date": shift.start_time.date(),
        "start_time": shift.start_time.time(),
        "end_time": shift.get_effective_end_time().time() if shift.get_effective_end_time() else None,

        # Minutos

        "duration_minutes": metrics["duration_minutes"],
        "delay_minutes": metrics["delay_minutes"],
        "extra_minutes": metrics['extra_minutes'],

        # Strings (UI)

        "duration": minutes_to_hhmm(metrics["duration_minutes"]),
        "delay": minutes_to_hhmm(-metrics["delay_minutes"]) if metrics["delay_minutes"] else "00:00",
        "extra": minutes_to_hhmm(metrics["extra_minutes"]) if metrics["extra_minutes"] else "00:00",

        "adjusted": shift.was_adjusted(),
    }

def totalize_report(rows):
    total_duration = 0
    total_delay = 0
    total_extra = 0

    for row in rows:
        if row['duration_minutes']:
            total_duration += row['duration_minutes']
        if row['delay_minutes']:
            total_delay += row['delay_minutes']
        if row['extra_minutes']:
            total_extra += row['extra_minutes']

    return {
        "total_duration": minutes_to_hhmm(total_duration),
        "total_delay": minutes_to_hhmm(-total_delay) if total_delay else "00:00",
        "total_extra": minutes_to_hhmm(total_extra) if total_extra else "00:00",
    }