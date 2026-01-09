from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django_extensions.management.commands.export_emails import full_name


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("O email é obrigatório")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self, username=None, email=None, password=None, **extra_fields
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_admin", True)

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    phone = models.CharField(max_length=20, blank=True, null=True, help_text="Telefone com DDD (ex: 21999998888")

    is_employee = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    objects: BaseUserManager = UserManager()  # type: ignore

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee")
    matricula = models.CharField(max_length=30, unique=True)
    ativo = models.BooleanField(default=True)
    jornada = models.TimeField(null=True, blank=True)
    signature = models.TextField(null=True, blank=True)
    base_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    base_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_display_name(self):
        full_name = self.user.get_full_name()
        return full_name if full_name else self.user.email


    def __str__(self):
        return f"{self.user.email} ({self.matricula})"


class UserDevice(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='device'
    )
    device_id = models.CharField(max_length=255)
    last_login = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.device_id}"


