from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from attendance.models import WorkShift, FraudAlert

def is_admin(user):
    return user.is_staff or user.is_superuser


@login_required
def fraud_dashboard(request):
    return render(request, "dashboard/fraudes.html")


@login_required
def dashboard_home(request):
    active_shifts_qs = (
        WorkShift.objects.filter(end_time__isnull=True)
        .select_related("employee", "employee__user")
        .order_by("-start_time")
    )
    active_shifts = [
        {
            "inspector_name": (
                shift.employee.user.get_full_name()
                or shift.employee.user.email
            ),
            "start_time": shift.start_time,
        }
        for shift in active_shifts_qs
    ]

    open_frauds = (
        FraudAlert.objects.filter(resolved=False)
        .order_by("-created_at")[:10]
    )

    context = {
        "active_shifts": active_shifts,
        "open_frauds": open_frauds,
    }

    return render(request, "dashboard/home.html", context)

@login_required
@login_required
def fraud_alerts_admin_json(request):
    try:
        print("Usuário:", request.user)
        if not request.user.is_staff and not request.user.is_superuser:
            return JsonResponse({"error": "Acesso negado"}, status=403)

        frauds = FraudAlert.objects.select_related("work_shift", "work_shift__employee", "work_shift__employee__user").all()
        data = []

        for f in frauds:
            data.append({
                "id": f.id,
                "employee_name": f.work_shift.employee.user.get_full_name() if f.work_shift and f.work_shift.employee else "N/A",
                "employee_email": f.work_shift.employee.user.email if f.work_shift and f.work_shift.employee else "N/A",
                "matricula": f.work_shift.employee.matricula if f.work_shift and f.work_shift.employee else "N/A",
                "fraud_type": f.fraud_type,
                "severity": f.severity,
                "score": f.score,
                "description": f.description,
                "created_at": f.created_at.isoformat(),
                "resolved": f.resolved,
            })
        return JsonResponse(data, safe=False)
    except Exception as e:
        import traceback
        print("ERRO na view de fraudes:", e)
        traceback.print_exc()
        return JsonResponse({"error": "Erro interno no servidor"}, status=500)


@login_required
def workshift_report_view(request):
    return render(request, "attendance/workshift_report.html")