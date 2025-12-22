from pydoc import resolve

from django.contrib import admin
from .models import WorkShift, FraudAlert


@admin.register(WorkShift)
class WorkShiftAdmin(admin.ModelAdmin):
    list_display = ("id", "employee", "start_time", "end_time", "status",)
    list_filter = ("employee",)

@admin.register(FraudAlert)
class FraudAlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'fraud_type', 'short_description', 'created_at', 'resolved',)
    list_filter = ('fraud_type', 'resolved', 'created_at',)
    search_fields = ('user__email', 'description',)
    ordering = ('-created_at',)
    actions = ['mark_as_resolved']
    def short_description(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description

    short_description.short_description = 'Descrição'

    def mark_as_resolved(self, request, queryset):
        queryset.update(resolved=True)
    mark_as_resolved.short_description = 'Marcar como resolvido'