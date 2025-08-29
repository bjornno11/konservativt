from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

SENTRAL_GROUP = "sentralstyret"

def user_in_sentral(user):
    return user.is_active and (user.is_superuser or user.groups.filter(name=SENTRAL_GROUP).exists())

def sentral_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if user_in_sentral(request.user):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Du har ikke tilgang til Sentralstyret.")
    return _wrapped
