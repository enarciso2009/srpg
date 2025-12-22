from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import UserDevice
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        request = self.context["request"]
        device_id = request.data.get("device_id")

        if not device_id:
            raise ValidationError({
                "device_id": "device_id é obrigatório"
            })

        data = super().validate(attrs)
        user = self.user

        # Verifica se o usuário já tem device registrado
        try:
            user_device = UserDevice.objects.get(user=user)

            if user_device.device_id != device_id:
                raise ValidationError("Este usuário já está logado em outro dispositivo")

            # Atualiza último login
            user_device.save()

        except UserDevice.DoesNotExist:
            # Primeiro login → registra o device
            UserDevice.objects.create(
                user=user,
                device_id=device_id
            )

        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        device_id = request.data.get('device_id')

        if not email or not password or not device_id:
            return Response({'error': "email, password e device_id são obrigatórios"},
                            status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=email, password=password)

        if not user:
            return Response(
                {'error': 'Credenciais inválidas'},
                status=status.HTTP_401_UNAUTHORIZED)

        # Controle de dispositivo
        device, created = UserDevice.objects.get_or_create(
            user=user,
            defaults={"device_id": device_id}
        )

        if not created and device.device_id != device_id:
            return Response(
                {'error': "Usuário já está logado em outro dipositivo"},
                status=status.HTTP_403_FORBIDDEN)

        # Gera tokens JWT
        refresh = RefreshToken.for_user(user)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "device_id": device.device_id
        })
