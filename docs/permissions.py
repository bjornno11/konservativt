# docs/permissions.py
from django.apps import apps

def M(name: str):
    return apps.get_model('docs', name)

def _user_in_groups(user, group_qs):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    user_gids = set(user.groups.values_list("id", flat=True))
    folder_gids = set(group_qs.values_list("id", flat=True))
    return bool(user_gids & folder_gids)

def user_has_folder_perm(user, folder, action: str) -> bool:
    """
    action: 'view' (liste/lese i mappe) eller 'add' (laste opp i mappe)
    """
    if action == "view":
        # skrivegruppe impliserer lese
        return _user_in_groups(user, folder.can_read.all()) or _user_in_groups(user, folder.can_write.all())
    if action == "add":
        return _user_in_groups(user, folder.can_write.all())
    return False

def user_has_doc_perm(user, doc, action: str) -> bool:
    """
    action: 'view' | 'edit' | 'delete'
    Eier (opprettet_av) kan alltid view/edit sitt eget dokument.
    """
    if not user.is_authenticated:
        return False
    # Eier: se/endre/slette eget
    if getattr(doc, "opprettet_av_id", None) == getattr(user, "id", None):
        if action in {"view", "edit", "delete"}:
            return True

    folder = doc.folder
    if action == "view":
        return user_has_folder_perm(user, folder, "view")
    if action in {"edit", "delete"}:
        return user_has_folder_perm(user, folder, "add")
    return False
