# members/queries.py
from django.db.models import Q
from .models import Medlem

def pending_qs(qs=None):
    qs = qs or Medlem.objects.all()
    # Pending = selvregistrering uten verver
    return qs.filter(
        verve_kilde="self",
        verver_user__isnull=True,
    ).filter(Q(verver_navn__isnull=True) | Q(verver_navn=""))
