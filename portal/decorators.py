from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*group_names):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not request.user.groups.filter(name__in=group_names).exists() and not request.user.is_superuser:
                raise PermissionDenied("You do not have access to this page.")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
