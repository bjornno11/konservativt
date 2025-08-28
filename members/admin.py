# members/admin.py
print(">>> Laster FULL members.admin (prod) <<<")

from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Q, Count, Case, When, Value, IntegerField
from django.utils.html import format_html
from django.urls import reverse

from .models import (
    Fylkeslag,
    Fylkeslagsmedlemskap,
    Medlem,
    Lokallag,
    Medlemskap,
    PendingMedlem,
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
    list_display = ("navn", "fylke", "lokallag_antall", "se_lokallag", "leder_navn")
    search_fields = ("navn", "fylke__navn")
    list_filter = ("fylke",)
    inlines = [FylkeslagsmedlemskapInline]

    def lokallag_antall(self, obj):
        return obj.fylke.lokallag.count()
    lokallag_antall.short_description = "Lokallag"

    def se_lokallag(self, obj):
        url = reverse("admin:members_lokallag_changelist")
        return format_html('<a href="{}?fylke__id__exact={}">Se lokallag</a>', url, obj.fylke_id)
    se_lokallag.short_description = ""

    def leder_navn(self, obj):
        # hent evt. leder(e) via Fylkeslagsmedlemskap
        ledere = (Fylkeslagsmedlemskap.objects
                  .filter(fylkeslag=obj, rolle="leder")
                  .select_related("medlem")
                  .order_by("-startdato"))
        names = [f"{fm.medlem.fornavn} {fm.medlem.etternavn}" for fm in ledere if fm.medlem_id]
        return ", ".join(names) if names else "—"
    leder_navn.short_description = "Leder"


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
