from django.contrib import admin
from .models import Employee, User, UserDevice

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "is_employee", "is_admin", "is_active")
    search_fields = ("email",)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("user", "matricula", "ativo")
    search_fields = ("matricula", "user_email")

@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "device_id")