# access/utils.py
from .models import RoleAssignment, OrgLevel

def user_has_level_access(user, level, org_id=None, required_roles: list[str] | None = None):
    qs = RoleAssignment.objects.filter(user=user, level=level)
    if org_id is None:
        qs = qs.filter(org_id__isnull=True) | qs.filter(org_id=0)
    else:
        qs = qs.filter(org_id=org_id)
    if required_roles:
        qs = qs.filter(role__name__in=required_roles)
    return qs.exists()
