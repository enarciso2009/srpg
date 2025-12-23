from rest_framework.exceptions import PermissionDenied, ValidationError
from decimal import Decimal
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.models import Employee, UserDevice
from .models import WorkShift, WorkShiftTracking, WorkShiftLocation, FraudAlert
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.utils.dateparse import parse_date
from django.db.models import F, ExpressionWrapper, DurationField
from datetime import timedelta
from math import radians, cos, sin, asin, sqrt
from .utils.antifraud import distance_km
from .serializers import (WorkShiftSerializer, WorkShiftTrackingSerializer,
                          WorkShiftLocationSerializer, FraudAlertSerializer)
from drf_spectacular.utils import (extend_schema, OpenApiExample, OpenApiResponse)



def haversine(lat1, lon1, lat2, lon2):
    """
    Retorna distancia em km entre dois pontos GPS
    """
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 -lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

def validate_shift_location(lat1, lon1, lat2, lon2, max_distance_m=200):
    distance_km = haversine(lat1, lon1, lat2, lon2)
    distance_m = distance_km * 1000
    if distance_m > max_distance_m:
        raise PermissionDenied(f'Fora do raio permitido ({int(distance_m)}m)')


def validate_user_device(user, device_id):
    try:
        device = UserDevice.objects.get(user=user)
    except UserDevice.DoesNotExist:
        raise PermissionDenied('Dispositivo não registrado')
    if device.device_id != device_id:
        raise PermissionDenied('Dispositivo não autorizado')

def parse_coordinate(value):
    """Tenta converter para float, retorna None se invalido"""
    try:
        return Decimal(value)
    except (TypeError, ValueError):
        return None

def create_fraud_alert(user, fraud_type, description, work_shift=None):
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


class StartShiftView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(
        tags=["Attendance"],
        summary="Iniciar jornada de trabalho",
        description=(
            'Inicia uma nova jornada de trabalho para o colaborador autenticado. '
            'É obrigatorio informar o dispositivo e a localização inicial. '
        ),
        request={
            "application/json":{
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "example": "DEVICE123"
                    },
                    "latitude": {
                        "type": "number",
                        "example": -23.5505
                    },
                    "longitude": {
                        "type": "number",
                        "example": -46.6333
                    }
                },
                "required": ["device_id", "latitude", "longitude"]
            }
        },
        responses={
            201: OpenApiResponse(
                description="Jornada iniciada com sucesso",
                examples=[
                    OpenApiExample(
                        "Sucesso",
                        value={
                            "id": 1,
                            "start_time": "2025-01-01T08:00:00Z",
                            "status": "ACTIVE"
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description="Dados inválidos ou dispositivo ausente",
                examples=[
                    OpenApiExample(
                        "Erro",
                        value={
                            "error": "Device ID is required"
                        }
                    )
                ]
            ),
            401: OpenApiResponse(description="usuário não autenticado"),
        }
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        device_id = request.data.get("device_id")
        if not device_id:
            return Response(
                {'error': "device_id é obrigatorio"},
                status=status.HTTP_400_BAD_REQUEST)
        validate_user_device(request.user, device_id)
        try:
            employee = user.employee
        except Employee.DoesNotExist:
            return Response({"error": "Funcionario não encontrado"},
                            status = status.HTTP_400_BAD_REQUEST)

        # Verifica se já existe turno aberto
        if WorkShift.objects.filter(employee=employee, end_time__isnull=True).exists():
            create_fraud_alert(
                user=user,
                fraud_type='MULTI_SHIFT',
                description='Tentativa de abrir dois turnos simultaneos')
            return Response({"error": "Já existe um turno aberto"},
                status=status.HTTP_400_BAD_REQUEST)

        lat = parse_coordinate(request.data.get("latitude"))
        lon = parse_coordinate(request.data.get("longitude"))

        if lat is None or lon is None:
            return Response({"error": "Latitude e Longitude válidas são obrigatórias"},
                status=status.HTTP_400_BAD_REQUEST)

        # Local base do funcionario (exemplo simples)
        base_lat = employee.base_latitude
        base_lon = employee.base_longitude

        if base_lat and base_lon:
            try:
                validate_shift_location(
                    float(base_lat),
                    float(base_lon),
                    float(lat),
                    float(lon)
                )
            except PermissionDenied as e:
                create_fraud_alert(
                    user=user,
                    fraud_type='LOCATION',
                    description=str(e)
                )
                raise

        last_shift = (WorkShift.objects.filter(employee=employee, end_time__isnull=False))
        if last_shift:
            dist = distance_km(
                last_shift.end_latitude,
                last_shift.end_longitude,
                lat,
                lon
            )
            if dist > 1:
                create_fraud_alert(
                    user=user,
                    work_shift=None,
                    fraud_type='LOCATION',
                    description=f'Start a {dist:.2f}km do último End'
                )


        shift = WorkShift.objects.create(
            employee=employee,
            start_latitude=lat,
            start_longitude=lon,
            start_time=timezone.now()
        )

        serializer = WorkShiftSerializer(shift)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EndShiftView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(
        tags=['Attendance'],
        summary="Encerrar jornada de trabalho",
        description=(
            "Encerra a jornada ativa do colaborador autenticado. "
            "É obrigatório informar a localização final."
        ),
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "example": -23.5510
                    },
                    "longitude": {
                        "type": "number",
                        "example": -46.6340
                    }
                },
                "required": ["latitude", "longitude"]
            }
        },
        responses={
            200: OpenApiResponse(
                description="Jornada encerrada com sucesso",
                examples=[
                    OpenApiExample(
                        "Sucesso",
                        value={
                            "id": 1,
                            "end_time": "2025-01-01T17:00:00Z",
                            "status": "FINISHED"
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description="Nenhuma jornada ativa encontrada",
                examples=[
                    OpenApiExample(
                        "Sem jornada",
                        value={
                            "error": "No active shift found"
                        }
                    )
                ]
            ),
            401: OpenApiResponse(description="Usuário não autenticado"),
        }
    )

    def post(self, request, *args, **kwargs):
        user = request.user
        device_id = request.data.get('device_id')
        if not device_id:
            return Response(
                {'error': 'device_id é obrigatorio'},
                status=status.HTTP_400_BAD_REQUEST
            )
        validate_user_device(request.user, device_id)
        try:
            employee = user.employee
        except Employee.DoesNotExist:
            return Response({"error": "Nenhum turno aberto encontrado"},
                status=status.HTTP_400_BAD_REQUEST)
        try:
            shift = WorkShift.objects.get(employee=employee, end_time__isnull=True)
        except WorkShift.DoesNotExist:
            return Response({"error": "Nenhum turno aberto encontrado."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Pega latitude/longitude do request
        lat = parse_coordinate(request.data.get("latitude"))
        lon = parse_coordinate(request.data.get("longitude"))

        if lat is None or lon is None:
            return Response(
                {"error": "Latitude e Longitude válidas são obrigatorias"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Tempo minimo de turno (5 minutos)
        min_duration = timedelta(minutes=5)
        worked_time = timezone.now() - shift.start_time
        if worked_time < min_duration:
            create_fraud_alert(
                user=user,
                work_shift=shift,
                fraud_type='TIME',
                description='Tentativa de encerrar turno antes do tempo minimo'
            )
            return Response({"error": "Tempo mínimo de turno não atingido"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Validar distância do local inicial
        try:
            validate_shift_location(
                float(shift.start_latitude),
                float(shift.start_longitude),
                float(lat),
                float(lon)
            )
        except PermissionDenied as e:
            create_fraud_alert(
                user=user,
                work_shift=shift,
                fraud_type='LOCATION',
                description=str(e)
            )
            raise

        shift.end_latitude = lat
        shift.end_longitude = lon
        shift.end_time = timezone.now()
        shift.save()

        serializer = WorkShiftSerializer(shift)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ShiftListView(generics.ListAPIView):
    """
    Lista todos os turnos do usuario autenticado
    """
    serializer_class = WorkShiftSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        try:
            employee = user.employee
        except Employee.DoesNotExist:
            return WorkShift.objects.none()

        return WorkShift.objects.filter(employee=employee).order_by('-start_time')


class ShiftListAllView(generics.ListAPIView):
    queryset = WorkShift.objects.all()
    serializer_class = WorkShiftSerializer
    permission_classes = [permissions.IsAdminUser]


class ShiftFilteredView(generics.ListAPIView):
    serializer_class = WorkShiftSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = WorkShift.objects.filter(employee=user.employee)

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        status = self.request.query_params.get('status')

        if start_date:
            queryset = queryset.filter(start_time__date__gte=parse_date(start_date))
        if end_date:
            queryset = queryset.filter(end_time__date__lte=parse_date(end_date))
        if status:
            if status.lower() == "open":
                queryset = queryset.filter(end_time__isnull=True)
            elif status.lower() == 'closed':
                queryset = queryset.filter(end_time__isnull=False)
        return queryset

class ShiftReportView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        shifts = WorkShift.objects.annotate(
            duration=ExpressionWrapper(
                F('end_time') - F('start_time'),
                output_field=DurationField()
            )
        ).values('employee__user__email', 'start_time', 'end_time', 'duration')

        report = []
        for shift in shifts:
            report.append({
                'employee': shift['employee__user__email'],
                'start': shift['start_time'],
                'end': shift['end_time'],
                'horus_worked': shift['duration'].total_seconds() / 3600 if shift['duration'] else None
            })
        return Response(report)

class ShiftTrackingView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        tags=["Tracking"],
        summary="Localização em tempo real dos colaboradores",
        description=(
            "Retorna a última localização conhecida dos colaboradores"
            "que estão com jornada ativa no momento. "
            "Endpoint utilizado pelo painel da logística."
        ),
        responses={
            200: OpenApiResponse(
                description="Lista de colaboradores ativos com localização",
                examples=[
                    OpenApiExample(
                        "Tracking",
                        value=[
                            {
                                "user": "user1@test.com",
                                "latitude": -23.5505,
                                "longitude": -46.6333,
                                "last_update": "2025-01-01T10:45:00Z",
                                "shift_id": 12
                            }
                        ]
                    )
                ]
            ),
            403: OpenApiResponse(description="Permissão negada"),
            401: OpenApiResponse(description="Usuário não autenticado")
        }
    )

    def post(self, request):
        user = request.user

        # 1️⃣ Validar dispositivo
        device_id = request.data.get("device_id")
        if not device_id:
            return Response(
                {"detail": "device_id é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST
            )

        validate_user_device(user, device_id)

        # 2️⃣ Buscar turno aberto
        try:
            employee = user.employee
            work_shift = WorkShift.objects.get(
                employee=employee,
                end_time__isnull=True
            )
        except (Employee.DoesNotExist, WorkShift.DoesNotExist):
            return Response(
                {"detail": "Nenhum turno aberto"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3️⃣ Validar payload
        serializer = WorkShiftLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lat = serializer.validated_data["latitude"]
        lng = serializer.validated_data["longitude"]

        # 4️⃣ GPS inválido
        if lat == 0 or lng == 0:
            create_fraud_alert(
                user=user,
                work_shift=work_shift,
                fraud_type='TRACKING',
                description='GPS inválido (0,0)'
            )
            return Response(
                {"detail": "Localização inválida"},
                status=status.HTTP_400_BAD_REQUEST
            )
        # 5️⃣ Buscar último ponto
        last_location = WorkShiftLocation.objects.filter(
            work_shift=work_shift
        ).order_by("-created_at").first()

        # 6️⃣ Antispam + teleporte
        if last_location:
            delta = timezone.now() - last_location.created_at

            # mínimo 60s entre pontos
            if delta < timedelta(seconds=60):
                create_fraud_alert(
                    user=user,
                    work_shift=work_shift,
                    fraud_type='TRACKING',
                    description='Envio excessivo de localização'
                )
                return Response(
                    {"detail": "Aguarde antes de enviar nova localização"},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

            # velocidade irreal
            distance_km = haversine(
                float(last_location.latitude),
                float(last_location.longitude),
                float(lat),
                float(lng),
            )

            hours = delta.total_seconds() / 3600
            if hours > 0:
                speed = distance_km / hours
                if speed > 150:
                    create_fraud_alert(
                        user=user,
                        work_shift=work_shift,
                        fraud_type='TRACKING',
                        description=f'Velocidade irreal detectada: {int(speed)} km/h'
                    )
                    return Response(
                        {"detail": "Movimentação irreal detectada"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # 7️⃣ Salvar localização
        WorkShiftLocation.objects.create(
            work_shift=work_shift,
            latitude=lat,
            longitude=lng
        )

        return Response(
            {"detail": "Localização registrada com sucesso"},
            status=status.HTTP_201_CREATED
        )

class FraudAlertListView(generics.ListAPIView):
    serializer_class = FraudAlertSerializer
    permission_classes = [IsAuthenticated]
    @extend_schema(
        tags=["Fraud"],
        summary="Listar alertas de fraude do usuário",
        description=(
            "Retorna todos os alertas de fraude associados ao usuário autenticado. "
            "Este endpoint é destinado ao próprio colaborador."
        ),
        responses={
            200: OpenApiResponse(
                description="Lista de alertas de fraude",
                examples=[
                    OpenApiExample(
                        "Lista",
                        value=[
                            {
                                "id": 1,
                                "score": 85,
                                "severity": 'HIGH',
                                "resolved": False,
                                "created_at": "2025-01-01T10:30:00Z"
                            }
                        ]
                    )
                ]
            ),
            401: OpenApiResponse(description="Usuário não autenticado"),
        }
    )

    def get_queryset(self):
        return FraudAlert.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

class FraudAlertAdminListView(generics.ListAPIView):
    serializer_class = FraudAlertSerializer
    permission_classes = [IsAdminUser]
    @extend_schema(
        tags=["Fraud"],
        summary="Listar todos os alertas de fraude (Admin)",
        description=(
            "Retorna todos os alertas de fraude do sistema. "
            "Acesso restrito a usuários administrativos."
        ),
        responses={
            200: OpenApiResponse(
                description="Lista completa de fraudes",
                examples=[
                    OpenApiExample(
                        "Admin",
                        value=[
                            {
                                "id": 1,
                                "user": "user1@test.com",
                                "score": 92,
                                "severity": "CRITICAL",
                                "resolved": False,
                                "created_at": "2025-01-01T11:00:00Z"
                            }
                        ]
                    )
                ]
            ),
            403: OpenApiResponse(description="Permissao negada"),
            401: OpenApiResponse(description="Usuário não autenticado"),
        }
    )

    def get_queryset(self):
        return FraudAlert.objects.all().order_by('-created_at')

class FraudAlertResolveView(APIView):
    permission_classes = [IsAdminUser]
    @extend_schema(
        tags=['Fraud'],
        summary="Resolver alterta de fraude",
        description=(
            "Marca um alerta de fraude como resolvido. "
            "Acesso restrito a adminitradores."
        ),
        responses={
            200: OpenApiResponse(
                description="Fraude resolvida com sucesso",
                examples=[
                    OpenApiExample(
                        "Resolvido",
                        value={
                            "id": 1,
                            "resolved": True
                        }
                    )
                ]
            ),
            404: OpenApiResponse(description="Alerta de fraude não encontrado"),
            403: OpenApiResponse(description="Permissão negada"),
            401: OpenApiResponse(description="Usuário não autenticado"),
        }
    )

    def post(self, request, pk):
        try:
            alert = FraudAlert.objects.get(pk=pk)
        except FraudAlert.DoesNotExist:
            return Response({'detail': 'Alerta não encontrado'},
                            status=status.HTTP_404_NOT_FOUND)
        alert.resolved = True
        alert.save()

        return Response({"detail": "Alerta reslvido com sucesso"})

class FraudScoreView(APIView):
    permission_classes = [IsAdminUser]

    def get(selfself, request, user_id):
        total = FraudAlert.objects.filter(user_id=user_id).aggregate(
            total=models.Sum('score')
        )["total"] or 0
        return Response({
            "user_id": user_id,
            "risk_score": total
        })