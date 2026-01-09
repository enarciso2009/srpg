from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.authentication import SessionAuthentication
from django.http import JsonResponse, HttpResponse
from rest_framework.exceptions import PermissionDenied
from decimal import Decimal
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.models import Employee, UserDevice
from .models import WorkShift, WorkShiftLocation, FraudAlert
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.utils.dateparse import parse_date
from math import radians, cos, sin, asin, sqrt
from attendance.services.workshift_service import end_shift, start_shift, validate_user_device, track_location, \
    adjust_shift_end, build_shift_report_row, totalize_report, get_workshifts_for_user
from .utils.antifraud import haversine
from .serializers import WorkShiftSerializer, WorkShiftLocationSerializer, FraudAlertSerializer
from drf_spectacular.utils import (extend_schema, OpenApiExample, OpenApiResponse)
from django.template.loader import render_to_string
from weasyprint import HTML
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime



@api_view(["POST"])
@permission_classes([IsAuthenticated])

def save_signature_api(request):
    print("CHEGOU NA SAVE_SIGNATURE_API")
    print("USER", request.user)
    print("DATA", request.data)

    employee = Employee.objects.get(user=request.user)
    signature_base64 = request.data.get("signature")

    if not signature_base64:
        return Response(
            {"error": "Assinatura não enviada"},
            status=400
        )
    employee.signature = signature_base64
    employee.save()

    return Response({"sucess": True})




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def workshift_report_pdf_api(request):
    user = request.user
    employee = user.employee
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    print("CHEGOU NA VIEW PDF")
    print("USER:", request.user)
    print("AUTH:", request.headers.get("Authorization"))

    # Converte string para date se informado
    try:
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        start_date = end_date = None

    # Pega os workshifts e totais

    rows, totals = get_workshifts_for_user(user, start_date, end_date)

    html_string = render_to_string(
        "attendance/workshift_report_pdf.html",
        {
            "user": user,
            "employee": employee,
            "rows": rows,
            "totals": totals,
            "start_date": start_date,
            "end_date": end_date,
            "signature_base64": employee.signature,
            "signature_rotated": True,
            "signed_at": timezone.now(),
        }
    )

    pdf_file = HTML(string=html_string).write_pdf()


    # Retorna PDF como resposta

    response = HttpResponse(pdf_file, content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename="relatorio_jornadas_{user.username}.pdf"'
    return response



@login_required
def workshift_report_pdf_view(request):
    user = request.user

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Pega os workshifts e totais
    rows, totals = get_workshifts_for_user(user, start_date, end_date)

    html_string = render_to_string(
        "attendance/workshift_report_pdf.html",
        {
            "user": user,
            "rows": rows,
            "totals": totals,
            "start_date": start_date,
            "end_date": end_date,
            "signature_base64": request.GET.get("signature")  # Base64 do mobile
        }
    )

    pdf_file = HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf_file, content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename="relatorio_jornadas_{user.username}.pdf"'
    return response



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
        user =request.user
        device_id = request.data.get("device_id")

        if not device_id:
            return Response({"error": "device_id é obrigatŕio"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_user_device(user, device_id)

            shift = start_shift(
                user,
                request.data.get("latitude"),
                request.data.get("longitude")
            )

        except PermissionDenied as e:
            print("erro ao iniciar turno:", str(e))
            print("Device Recebido:", device_id)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = WorkShiftSerializer(shift)
        return Response(serializer.data, status=status.HTTP_201_CREATED)



class EndShiftView(APIView):
    permission_classes = [IsAuthenticated]
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
            shift = end_shift(user, request.data.get("latitude"), request.data.get("longitude"))
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


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



class AdjustiShiftView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        tags=["Attendance"],
        summary="Ajustar encerramento de jornada",
        description=("Permite que um administrador ajuste manualmente o fim de uma jornada esquecida pelo vistoriador.")
    )
    def post(selfself, request, pk):
        adjusted_end_time = request.data.get("adjusted_end_time")
        reason = request.data.get("reason")

        if not adjusted_end_time + request.data.get("adjusted_end_time"):
            reason = request.data.get("reason")

            if not adjusted_end_time or not reason:
                return Response(
                    {"error": "adjusted_end_time e reason são obrigatorios"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                adjusted_end_time = timezone.make_aware(
                    timezone.datetime.fromisoformat(adjusted_end_time)
                )
            except Exception:
                return Response(
                    {"error": "Formato de data invalido"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                shift = adjust_shift_end(
                    shift_id=pk,
                    adjusted_end_time=adjusted_end_time,
                    reason=reason,
                    admin_user=request.user
                )
            except PermissionDenied as e:
                return Response({"error": str(e)}, status=status.http_400_BAD_REQUEST)

            serializer = WorkShiftSerializer(shift)
            return Response(serializer.data, status.HTTP_200_OK)



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
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Attendance'],
        summary="Relatorio de jornadas",
        description=("Retorna relatorios de entrada e saida com duração, "
                     "atrasos, horas extras e totalização"
                     )
    )
    def get(self, request):
        user = request.user
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        try:
            employee = user.employee
            queryset = WorkShift.objects.filter(employee=employee)
        except Employee.DoesNotExist:
            return Response(
                {"rows": [], "totals": {}},
                status=status.HTTP_200_OK
            )

        if start_date:
            queryset = queryset.filter(start_time__date__gte=parse_date(start_date))
        if end_date:
            queryset = queryset.filter(start_time__date__lte=parse_date(end_date))

        queryset = queryset.order_by("start_time")

        rows = []
        for shift in queryset:
            row = build_shift_report_row(shift)
            rows.append(row)

        totals = totalize_report(rows)

        return Response({
            "rows": rows,
            "totals": totals
        }, status=status.HTTP_200_OK)



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
        device_id = request.data.get("device_id")
        if not device_id:
            return Response({"detail": "device_id é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)


        validate_user_device(user, device_id)

        serializer = WorkShiftLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            track_location(user, serializer.validated_data["latitude"], serializer.validated_data["longitude"])
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=400)

        return Response({"detail": "Localização registrada com sucesso"}, status=201)


class ShiftTrackingDashboardView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Tracking"],
        summary="Tracking para dashboard",
        description="Retorna a última localização dos colaboradores com turno ativo",
    )
    def get(self, request):
        active_shifts = WorkShift.objects.filter(
            end_time__isnull=True
        ).select_related("employee", "employee__user")

        result = []

        for shift in active_shifts:
            last_location = WorkShiftLocation.objects.filter(
                work_shift=shift
            ).order_by("-created_at").first()

            if not last_location:
                continue

            result.append({
                "inspector_id": shift.employee.id,
                "name": shift.employee.user.get_full_name() or shift.employee.user.username,
                "phone": shift.employee.user.phone,
                "latitude": float(last_location.latitude),
                "longitude": float(last_location.longitude),
                "last_update": last_location.created_at,
                "shift_id": shift.id,
            })
        return Response(result)



class FraudAlertListView(generics.ListAPIView):
    serializer_class = FraudAlertSerializer
    authentication_classes = [SessionAuthentication]
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
        return FraudAlert.objects.select_related(
            "work_shift",
            "work_shift__employee",
            "work_shift__employee__user"
        ).order_by('-created_at')



class FraudAlertAdminListView(generics.ListAPIView):
    serializer_class = FraudAlertSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

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
        qs = (FraudAlert.objects.select_related("work_shift__employee__user").order_by('-created_at')
        )
        severity = self.request.query_params.get("severity")
        resolved = self.request.query_params.get("resolved")
        employee = self.request.query_params.get("employee")

        if severity:
            qs = qs.filter(severity=severity)

        if resolved is not None:
            qs = qs.filter(resolved=resolved.lower() == 'true')

        if employee:
            qs = qs.filter(
                work_shift__employee__user__email__icontains=employee
            )
        return qs


class FraudAlertResolveView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]
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
        if alert.resolved:
            return Response(
                {'detail': "Este alerta já está resolvido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        alert.resolved = True
        alert.save(update_fields=['resolved'])

        return Response({"id": alert.id,
                         "resolved": True,
                         "resolved_at": timezone.now()
        })

class FraudScoreView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(selfself, request, user_id):
        total = FraudAlert.objects.filter(user_id=user_id).aggregate(
            total=models.Sum('score')
        )["total"] or 0
        return Response({
            "user_id": user_id,
            "risk_score": total
        })


@login_required
def frauds_admin_list(request):
    """
    Retorna todos os alertas de fraude ordenados por criação
    Acesso igual ao dashboard, sem necessidade de JWT.
    """
    alerts = FraudAlert.objects.select_related(
        "work_shift__employee__user"
    ).order_by("-created_at")

    data = []
    for alert in alerts:
        employee_name = "N/A"
        matricula = "N/A"

        if alert.work_shift and alert.work_shift.employee:
            user = getattr(alert.work_shift.employee, "user", None)
            employee_name = user.get_full_name() if user else "N/A"
            matricula = getattr(alert.work_shift.employee, "id", "N/A")

        data.append({
            "id": alert.id,
            "employee_name": employee_name,
            "matricula": matricula,
            "fraud_type": alert.fraud_type,
            "description": alert.description,
            "created_at": alert.created_at.isoformat(),
            "resolved": alert.resolved
        })
    return JsonResponse(data, safe=False)



