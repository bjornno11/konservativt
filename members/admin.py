# members/admin.py
#print(">>> Laster FULL members.admin (prod) <<<")

from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Q, Count, Case, When, Value, IntegerField
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.forms import PasswordResetForm
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.conf import settings

SENTRAL_GROUP_NAME = "sentralstyret"
def get_or_create_user_for_medlem(m):
    User = get_user_model()
    email = (m.epost or "").strip().lower()
    if not email:
        return None, "Medlem mangler e-post"

    # Finn eksisterende user (koblet eller via epost)
    u = m.user
    if not u:
        u = User.objects.filter(email=email).first()
    if not u:
        # Opprett ny bruker uten passord (bruker setter selv via lenke)
        # username = email (enkelt og greit)
        u = User.objects.create_user(username=email, email=email, password=None, is_active=True)
    # Koble hvis ikke allerede koblet
    if not m.user_id:
        m.user = u
        m.save(update_fields=["user"])
    return u, None


def ensure_sentral_group(user):
    g, _ = Group.objects.get_or_create(name=SENTRAL_GROUP_NAME)
    user.groups.add(g)
    return g


def send_set_password_email(request, user):
    """
    Bruk Djangos PasswordResetForm til å sende 'set your password'-lenke.
    Returnerer True hvis sendt OK, ellers False og evt. en URL du kan vise manuelt.
    """
    # Standardformularen krever at brukeren eksisterer i DB (det gjør den)
    form = PasswordResetForm({"email": user.email})
    if form.is_valid():
        try:
            form.save(
                request=request,
                use_https=True,
                email_template_name="registration/password_reset_email.html",  # valgfritt; bruker standard om ikke finnes
                subject_template_name="registration/password_reset_subject.txt",  # valgfritt
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            )
            return True, None
        except Exception:
            pass

    # Fallback: generer URL manuelt så admin kan kopiere den
    from django.contrib.auth.tokens import default_token_generator
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    # Standard URL for confirm-view (respekterer FORCE_SCRIPT_NAME)
    from django.urls import reverse
    path = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
    # Lag full URL (bruk request)
    scheme = "https"
    host = request.get_host()
    url = f"{scheme}://{host}{path}"
    return False, url


from .models import (
    Fylkeslag,
    Fylkeslagsmedlemskap,
    Medlem,
    Lokallag,
    Medlemskap,
    PendingMedlem,
    Rolle,
    SentralstyreMedlemskap,
)
from geo.models import Fylke, Kommune


# Hvis disse var registrert fra før i en tidligere runde, fjern dem trygt
for mdl in (Medlem, PendingMedlem):
    try:
        admin.site.unregister(mdl)
    except admin.sites.NotRegistered:
        pass


class MedlemskapInlineForPending(admin.TabularInline):
    model = Medlemskap
    extra = 1
    fields = ("lokallag", "startdato")
    readonly_fields = ("startdato",)

    _current_member = None  # settes per request

    def get_formset(self, request, obj=None, **kwargs):
        # obj er PendingMedlem-objektet i change-visningen
        self._current_member = obj
        return super().get_formset(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "lokallag" and self._current_member:
            m = self._current_member
            if m.kommune_id:
                # Kun lag i kandidatens fylke; lag i kandidatens kommune øverst
                qs = (Lokallag.objects
                      .filter(fylke_id=m.kommune.fylke_id)
                      .annotate(
                          prio=Case(
                              When(kommune_id=m.kommune_id, then=Value(0)),
                              default=Value(1),
                              output_field=IntegerField(),
                          )
                      )
                      .order_by("prio", "navn"))
                field.queryset = qs
            else:
                # Fallback: hvis kommunen ikke er satt, snevr til fylker medlemmet
                # ev. allerede har via lokallag (kan bli tomt — bedre enn “alle”)
                fylker = m.lokallag.values_list("fylke_id", flat=True)
                field.queryset = Lokallag.objects.filter(fylke_id__in=fylker).order_by("navn")
        return field


# ---------------- FILTERE ----------------

class ApprovedListFilter(admin.SimpleListFilter):
    title = "Status"
    parameter_name = "approved"

    def lookups(self, request, model_admin):
        return [("yes", "Godkjent"), ("no", "Pending (selvregistrert)")]

    def queryset(self, request, queryset):
        v = self.value()
        if v == "yes":
            return queryset.filter(verver_user__isnull=False)
        if v == "no":
            return queryset.filter(verver_user__isnull=True, verve_kilde="self").filter(
                Q(verver_navn__isnull=True) | Q(verver_navn="")
            )
        return queryset


class FylkeListFilter(admin.SimpleListFilter):
    title = "Fylke"
    parameter_name = "fylke"

    def lookups(self, request, model_admin):
        return list(Fylke.objects.order_by("navn").values_list("id", "navn"))

    def queryset(self, request, queryset):
        v = self.value()
        return queryset.filter(kommune__fylke_id=v) if v else queryset


class KommuneListFilter(admin.SimpleListFilter):
    title = "Kommune"
    parameter_name = "kommune"

    def lookups(self, request, model_admin):
        fylke_id = request.GET.get("fylke")
        qs = Kommune.objects.all()
        if fylke_id and str(fylke_id).isdigit():
            qs = qs.filter(fylke_id=int(fylke_id))
        return list(qs.order_by("navn").values_list("id", "navn"))

    def queryset(self, request, queryset):
        v = self.value()
        return queryset.filter(kommune_id=v) if v else queryset


class LokallagListFilter(admin.SimpleListFilter):
    title = "Lokallag"
    parameter_name = "lokallag"

    def lookups(self, request, model_admin):
        fylke_id = request.GET.get("fylke")
        kommune_id = request.GET.get("kommune")
        qs = Lokallag.objects.all()
        if fylke_id and str(fylke_id).isdigit():
            qs = qs.filter(fylke_id=int(fylke_id))
        if kommune_id and str(kommune_id).isdigit():
            qs = qs.filter(kommune_id=int(kommune_id))
        return list(qs.order_by("navn").values_list("id", "navn"))

    def queryset(self, request, queryset):
        v = self.value()
        return queryset.filter(lokallag__id=v) if v else queryset

class FylkeslagFilter(admin.SimpleListFilter):
    title = "Fylkeslag"
    parameter_name = "fylkeslag"

    def lookups(self, request, model_admin):
        return list(Fylkeslag.objects.order_by("navn").values_list("id", "navn"))

    def queryset(self, request, queryset):
        v = self.value()
        if v:
            # Krever at du har modellen Fylkeslagsmedlemskap (med medlem FK)
            return queryset.filter(fylkeslagsmedlemskap__fylkeslag_id=v)
        return queryset



# ------------- INLINE FOR M2M -------------


class MedlemskapInline(admin.TabularInline):
    model = Medlemskap
    fk_name = "medlem"         # viktig for PendingMedlem (proxy)
    extra = 0
    # IKKE bruk autocomplete her – vi filtrerer manuelt:
    # autocomplete_fields = ("lokallag",)

    fields = ("lokallag", )
    # Om du vil vise flere kolonner i inlinen kan du legge til, f.eks. startdato som readonly:
    # readonly_fields = ("startdato",)

    # Heng fylke-id fra parent-objektet på inlinen (kalles én gang pr. visning)
    _current_fylke_id = None
    _current_kommune_id = None

    def get_formset(self, request, obj=None, **kwargs):
        # obj er Medlem/PendingMedlem i change-visning
        self._current_fylke_id = getattr(getattr(obj, "kommune", None), "fylke_id", None)
        self._current_kommune_id = getattr(obj, "kommune_id", None)
        return super().get_formset(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "lokallag" and self._current_fylke_id:
            # Filtrer til riktig fylke, og prioriter lag i medlemmets kommune øverst
            qs = (Lokallag.objects
                  .filter(fylke_id=self._current_fylke_id)
                  .annotate(
                      prio=Case(
                          When(kommune_id=self._current_kommune_id, then=Value(0)),
                          default=Value(1),
                          output_field=IntegerField(),
                      )
                  )
                  .order_by("prio", "navn"))
            field.queryset = qs
        return field


class FylkeslagsmedlemskapInline(admin.TabularInline):
    """
    Inline på Fylkeslag – velg kun medlemmer som faktisk har lokallag i dette fylket.
    """
    model = Fylkeslagsmedlemskap
    extra = 1
    can_delete = True
    min_num = 0
    max_num = 1000
    autocomplete_fields = ("medlem",)
    fields = ("medlem", "rolle", "startdato")
    readonly_fields = ("startdato",)

    _current_fylke_id = None  # settes per request

    def get_formset(self, request, obj=None, **kwargs):
        # obj er Fylkeslag-objektet i change-visning
        self._current_fylke_id = getattr(obj, "fylke_id", None)
        return super().get_formset(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "medlem" and self._current_fylke_id:
            field.queryset = Medlem.objects.filter(
                lokallag__fylke_id=self._current_fylke_id
            ).distinct()
        return field


class FylkeslagsmedlemskapInlineForMember(admin.TabularInline):
    """
    Inline på Medlem – tillat kun fylkeslag i fylke(r) hvor medlemmet har lokallag.
    """
    model = Fylkeslagsmedlemskap
    extra = 0
    autocomplete_fields = ("fylkeslag",)
    fields = ("fylkeslag", "rolle", "startdato")
    readonly_fields = ("startdato",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "fylkeslag":
            obj_id = request.resolver_match.kwargs.get("object_id")
            if obj_id:
                m = Medlem.objects.filter(pk=obj_id).first()
                if m:
                    fylker = m.lokallag.values_list("fylke_id", flat=True)
                    field.queryset = Fylkeslag.objects.filter(
                        fylke_id__in=fylker
                    ).distinct()
        return field


# ------------- ADMIN-KLASSER -----------------

@admin.register(Lokallag)
class LokallagAdmin(admin.ModelAdmin):
    list_display = ("navn", "fylke", "kommune")
    list_filter = ("fylke", "kommune")
    search_fields = ("navn", "fylke__navn", "kommune__navn")  # for autocomplete-oppslag fra andre admin


@admin.register(Fylkeslag)
class FylkeslagAdmin(admin.ModelAdmin):
    # KUN felt vi vet finnes på modellen
    list_display  = ("id", "navn", "fylke", "leder_navn")      # 'fylke' er FK, trygt å vise
    search_fields = ("navn", "fylke__navn")
    list_filter   = ("fylke",)
    ordering      = ("navn", "id")

    # Viktig: ingen inlines her før siden laster stabilt
    inlines = [FylkeslagsmedlemskapInline]

@admin.register(Medlem)
class MedlemAdmin(admin.ModelAdmin):
    list_display = (
        "etternavn", "fornavn",
        "telefon", "epost",
        "kommune", "fylke",
        "lokallag_list",
        "status", "registrert",
    )
    search_fields = ("fornavn", "etternavn", "telefon", "epost", "adresse")
    list_filter = (
        ApprovedListFilter,
        FylkeListFilter,
        KommuneListFilter,
        LokallagListFilter,
        FylkeslagFilter, 
    )
    ordering = ("etternavn", "fornavn", "id")
    inlines = [MedlemskapInline, FylkeslagsmedlemskapInlineForMember]
    list_select_related = ("kommune", "kommune__fylke")
    preserve_filters = False

    def fylke(self, obj):
        return obj.kommune.fylke.navn if obj.kommune_id else ""
    fylke.admin_order_field = "kommune__fylke__navn"

    def lokallag_list(self, obj):
        names = [l.navn for l in obj.lokallag.all()]
        return ", ".join(names) if names else "—"
    lokallag_list.short_description = "Lokallag"

    def status(self, obj):
        return "Godkjent" if obj.verver_user_id else "Pending"
    status.admin_order_field = "verver_user"


# ------------- PENDING-ADMIN --------------

def pending_filter(qs):
    return qs.filter(verve_kilde="self", verver_user__isnull=True).filter(
        Q(verver_navn__isnull=True) | Q(verver_navn="")
    )


@admin.action(description="Godkjenn valgte (krever lokallag)")
def approve_members(modeladmin, request, queryset):
    # Filtrer fortsatt bare "pending"
    qs = pending_filter(queryset).annotate(lag_count=Count("lokallag"))
    to_approve = qs.filter(lag_count__gt=0)
    lacking    = qs.filter(lag_count=0)

    if lacking.exists():
        # Vis en kort liste over hvem som mangler lokallag
        sample = ", ".join(
            f"{m['etternavn']}, {m['fornavn']} (id {m['id']})"
            for m in lacking.values("id", "fornavn", "etternavn")[:10]
        )
        more = " ..." if lacking.count() > 10 else ""
        messages.error(
            request,
            f"{lacking.count()} medlem(mer) mangler lokallag. "
            f"Åpne raden og legg til lokallag i inlinen før godkjenning. {sample}{more}"
        )

    if not to_approve.exists():
        if not lacking.exists():
            messages.info(request, "Ingen valgte rader å godkjenne.")
        return

    with transaction.atomic():
        updated = Medlem.objects.filter(
            id__in=list(to_approve.values_list("id", flat=True))
        ).update(
            verver_user=request.user,
            verver_navn=request.user.get_username(),
        )

    messages.success(request, f"Godkjente {updated} medlem(mer).")

@admin.register(PendingMedlem)
class PendingMedlemAdmin(admin.ModelAdmin):
    list_display  = ("etternavn", "fornavn", "telefon", "kommune", "lokallag_list", "registrert")
    search_fields = ("fornavn", "etternavn", "telefon", "epost")
    list_per_page = 50
    actions = [approve_members]
    inlines = [MedlemskapInlineForPending]   # ← legg til denne


    def get_queryset(self, request):
        # + prefetch lokallag for å unngå N+1
        qs = (super().get_queryset(request)
              .select_related("kommune", "kommune__fylke")
              .prefetch_related("lokallag"))
        return pending_filter(qs)

    def lokallag_list(self, obj):
        names = [l.navn for l in obj.lokallag.all()]
        return ", ".join(names) if names else "—"
    lokallag_list.short_description = "Lokallag"


    def has_view_permission(self, request, obj=None):
        u = request.user
        return u.is_active and (u.is_staff or u.is_superuser)

    def has_change_permission(self, request, obj=None):
        u = request.user
        return u.is_staff or u.is_superuser

    def has_add_permission(self, request):
        return False


@admin.register(Rolle)
class RolleAdmin(admin.ModelAdmin):
    list_display = ("navn", "kode", "scope", "rang")
    list_filter = ("scope",)
    search_fields = ("navn", "kode")
    ordering = ("scope", "rang", "navn")


@admin.action(description="Inviter til Sentralstyret (opprett bruker + send sett-passord)")
def invite_to_sentral(modeladmin, request, queryset):
    emailed = 0
    manual  = []

    for obj in queryset:
        # støtt både SentralstyreMedlemskap og Medlem som queryset
        medlem = getattr(obj, "medlem", None) or obj
        user, err = get_or_create_user_for_medlem(medlem)
        if err:
            messages.error(request, f"{medlem}: {err}")
            continue

        ensure_sentral_group(user)
        ok, url = send_set_password_email(request, user)
        if ok:
            emailed += 1
        else:
            manual.append((medlem, url))

    if emailed:
        messages.success(request, f"Sendte sett-passord-epost til {emailed} bruker(e).")
    if manual:
        lines = "\n".join([f"{m} → {u}" for m, u in manual])
        messages.warning(
            request,
            "Kunne ikke sende epost for noen – kopier lenkene og send manuelt:\n" + lines
        )


class SentralstyreMedlemskapInline(admin.TabularInline):
    model = SentralstyreMedlemskap
    extra = 0
    autocomplete_fields = ("rolle",)
    fields = ("rolle", "startdato", "sluttdato")
    readonly_fields = ("startdato",)

# Heng inlinen på Medlem-admin (uten å miste eksisterende inlines)
try:
    MedlemAdmin.inlines = list(getattr(MedlemAdmin, "inlines", [])) + [SentralstyreMedlemskapInline]
except NameError:
    pass


@admin.register(SentralstyreMedlemskap)
class SentralstyreMedlemskapAdmin(admin.ModelAdmin):
    list_display = ("medlem", "rolle", "startdato", "sluttdato", "er_aktiv")
    list_filter = ("rolle",)
    search_fields = ("medlem__fornavn", "medlem__etternavn", "rolle__navn")
    actions = [invite_to_sentral]   # ← LEGG TIL DENNE
    def er_aktiv(self, obj):
        return obj.aktiv
    er_aktiv.boolean = True
    er_aktiv.short_description = "Aktiv"
