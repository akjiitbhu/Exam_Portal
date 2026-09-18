from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard(request):
    is_coordinator = request.user.groups.filter(name="Coordinator").exists() or request.user.is_superuser
    is_staff_role = request.user.groups.filter(name="Staff").exists() or request.user.is_superuser
    return render(request, "portal/dashboard.html", {"is_coordinator": is_coordinator, "is_staff_role": is_staff_role})
