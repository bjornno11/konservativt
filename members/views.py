# members/views.py
# members/views.py
import logging
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.views.generic import CreateView, UpdateView, ListView, DetailView, TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.db.models import Q
from django.utils.functional import cached_property
from .models import Medlem, Medlemskap, Lokallag
from .forms import MedlemForm
from .queries import pending_qs
from geo.models import Fylke, Kommune, Postnummer
from .forms import SelfMedlemPublicForm
from django.db import transaction
from members.notifications import notify_new_self_registration

logger = logging.getLogger("members")

# -----------------------
# CRUD for Member
# -----------------------

# members/views.py (utdrag)

class MembersList(LoginRequiredMixin, ListView):
    model = Medlem
    template_name = "members/list.html"
    context_object_name = "members"
    paginate_by = 30

    @cached_property
    def f_id(self):
        v = (self.request.GET.get("f") or "").strip()
        return int(v) if v.isdigit() else None

    @cached_property
    def k_id(self):
        v = (self.request.GET.get("k") or "").strip()
        return int(v) if v.isdigit() else None

    @cached_property
    def l_id(self):
        v = (self.request.GET.get("l") or "").strip()
        return int(v) if v.isdigit() else None

    @cached_property
    def tel(self):
        return (self.request.GET.get("tel") or "").strip()

    @cached_property
    def q(self):
        return (self.request.GET.get("q") or "").strip()

    def get_queryset(self):
        qs = (
            Medlem.objects.all()
            .select_related("kommune", "kommune__fylke", "postnummer")
            .prefetch_related("lokallag")
            .order_by("etternavn", "fornavn", "id")
        )
        if self.f_id:
            qs = qs.filter(kommune__fylke_id=self.f_id)
        if self.k_id:
            qs = qs.filter(kommune_id=self.k_id)
        if self.l_id:
            qs = qs.filter(lokallag__id=self.l_id)
        if self.tel:
            qs = qs.filter(telefon__icontains=self.tel)
        if self.q:
            qs = qs.filter(
                Q(fornavn__icontains=self.q) |
                Q(etternavn__icontains=self.q) |
                Q(epost__icontains=self.q) |
                Q(adresse__icontains=self.q)
            )
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fylker = Fylke.objects.order_by("navn")
        kommuner = Kommune.objects.none()
        lag = Lokallag.objects.none()

        if self.f_id:
            kommuner = Kommune.objects.filter(fylke_id=self.f_id).order_by("navn")
            lag = Lokallag.objects.filter(fylke_id=self.f_id).order_by("navn")
        if self.k_id:
            lag = lag.filter(kommune_id=self.k_id) if lag.exists() else Lokallag.objects.filter(
                kommune_id=self.k_id
            ).order_by("navn")

        ctx.update(
            fylker=fylker,
            kommuner=kommuner,
            lokallag=lag,
            f=self.f_id, k=self.k_id, l=self.l_id,
            tel=self.tel, q=self.q,
        )
        return ctx


class MemberUpdate(LoginRequiredMixin, UpdateView):
    model = Medlem
    form_class = MedlemForm
    template_name = "members/form.html"

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.save()
        form.save_m2m()

        # Sync lokallag
        ids = [int(x) for x in self.request.POST.getlist("lokallag") if str(x).isdigit()]
        ønskede = set(ids)
        nåværende = set(
            Medlemskap.objects.filter(medlem=self.object).values_list("lokallag_id", flat=True)
        )
        slett = nåværende - ønskede
        if slett:
            Medlemskap.objects.filter(medlem=self.object, lokallag_id__in=slett).delete()
        add = ønskede - nåværende
        if add:
            Medlemskap.objects.bulk_create(
                [Medlemskap(medlem=self.object, lokallag_id=i) for i in add],
                ignore_conflicts=True,
            )

        messages.success(self.request, "Endringer lagret.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("members:detail", kwargs={"pk": self.object.pk})

class MembersList(LoginRequiredMixin, ListView):
    model = Medlem
    template_name = "members/list.html"
    context_object_name = "medlemmer"
    paginate_by = 30

    # --- filtre hentet fra GET ---
    @cached_property
    def f_id(self):
        v = (self.request.GET.get("f") or "").strip()
        return int(v) if v.isdigit() else None

    @cached_property
    def k_id(self):
        v = (self.request.GET.get("k") or "").strip()
        return int(v) if v.isdigit() else None

    @cached_property
    def l_id(self):
        v = (self.request.GET.get("l") or "").strip()
        return int(v) if v.isdigit() else None

    @cached_property
    def tel(self):
        return (self.request.GET.get("tel") or "").strip()

    @cached_property
    def q(self):
        return (self.request.GET.get("q") or "").strip()

    def get_queryset(self):
        qs = (
            Medlem.objects.all()
            .select_related("kommune", "kommune__fylke", "postnummer")
            .prefetch_related("lokallag")
            .order_by("etternavn", "fornavn", "id")
        )

        if self.f_id:
            qs = qs.filter(kommune__fylke_id=self.f_id)

        if self.k_id:
            qs = qs.filter(kommune_id=self.k_id)

        if self.l_id:
            qs = qs.filter(lokallag__id=self.l_id)

        if self.tel:
            qs = qs.filter(telefon__icontains=self.tel)

        if self.q:
            qs = qs.filter(
                Q(fornavn__icontains=self.q) |
                Q(etternavn__icontains=self.q) |
                Q(epost__icontains=self.q) |
                Q(adresse__icontains=self.q)
            )

        # M2M-filter (lokallag) kan gi duplikater → distinkt
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # nedtrekk: fylker alltid, kommuner/lokallag filtrert på valgt
        fylker = Fylke.objects.order_by("navn")
        kommuner = Kommune.objects.none()
        lag = Lokallag.objects.none()

        if self.f_id:
            kommuner = Kommune.objects.filter(fylke_id=self.f_id).order_by("navn")
            lag = Lokallag.objects.filter(fylke_id=self.f_id).order_by("navn")
        if self.k_id:
            lag = lag.filter(kommune_id=self.k_id) if lag.exists() else Lokallag.objects.filter(
                kommune_id=self.k_id
            ).order_by("navn")

        ctx.update(
            f=self.f_id,
            k=self.k_id,
            l=self.l_id,
            tel=self.tel,
            q=self.q,
            fylker=fylker,
            kommuner=kommuner,
            lokallag=lag,
        )
        return ctx

class MemberCreate(LoginRequiredMixin, CreateView):
    model = Medlem
    form_class = MedlemForm
    template_name = "members/form.html"
    success_url = reverse_lazy("members:list")

    def form_valid(self, form):
        # Passer request inn i form.save slik at verver_user kan settes
        obj = form.save(request=self.request)
        messages.success(self.request, f"Medlem «{obj.fornavn} {obj.etternavn}» er lagret.")
        return super().form_valid(form)

class MemberDetail(LoginRequiredMixin, DetailView):
    model = Medlem
    template_name = "members/detail.html"
    context_object_name = "medlem"
# members/views.py (legg til et sted under de andre CBV-ene)
from .forms import SelfMedlemPublicForm
from .models import Medlem

class SelfRegister(CreateView):
    model = Medlem
    form_class = SelfMedlemPublicForm
    template_name = "members/self_register.html"
    success_url = reverse_lazy("members:self-thanks")

    def form_valid(self, form):
        # 1) Lagre en gang, og behold objektet
        self.object = form.save(request=None)  # viktig: ingen innlogget verver settes
        # 2) Sørg for at M2M (lokallag) også lagres
        if hasattr(form, "save_m2m"):
            form.save_m2m()

        # 3) Send varsel-epost ETTER at transaksjonen er committed
        def _send():
            try:
                notify_new_self_registration(self.object)
                logging.getLogger(__name__).info(
                    "Varsel sendt ved self-registrering id=%s", getattr(self.object, "id", "?")
                )
            except Exception:
                logging.getLogger(__name__).exception(
                    "Varsel-epost feilet for id=%s", getattr(self.object, "id", "?")
                )

        transaction.on_commit(_send)

        # 4) Flash-melding og redirect
        messages.success(self.request, "Takk! Registreringen er mottatt.")
        return HttpResponseRedirect(self.get_success_url())


class SelfThanks(TemplateView):
    template_name = "members/self_thanks.html"


# -----------------------
# Hjelpe-endepunkter (GET)
# -----------------------
# --- HJELPE-ENDEPUNKTER (GET) ---

@method_decorator(require_GET, name="dispatch")
class HxKommuner(View):
    def get(self, request):
        fylke_id = request.GET.get("fylke")
        qs = Kommune.objects.all().order_by("navn")
        if fylke_id:
            qs = qs.filter(fylke_id=fylke_id)
        options = "".join(f'<option value="{k.id}">{k.navn}</option>' for k in qs)
        return HttpResponse(options or '<option value="">(Ingen kommuner)</option>')


@method_decorator(require_GET, name="dispatch")
class HxLokallag(View):
    def get(self, request):
        fylke_id = request.GET.get("fylke")
        kommune_id = request.GET.get("kommune")
        qs = Lokallag.objects.all().order_by("navn")
        if fylke_id:
            qs = qs.filter(fylke_id=fylke_id)
        if kommune_id:
            qs = qs.filter(kommune_id=kommune_id)
        options = "".join(f'<option value="{l.id}">{l.navn}</option>' for l in qs)
        return HttpResponse(options or '<option value="">(Ingen lag)</option>')


@method_decorator(require_GET, name="dispatch")
class HxPostnummer(View):
    def get(self, request):
        kommune_id = request.GET.get("kommune")
        qs = Postnummer.objects.all()
        if kommune_id:
            # bruk riktig related_name for kobling postnummer<->kommune
            qs = qs.filter(kommuner__kommune_id=kommune_id)
        qs = qs.distinct().order_by("nummer")

        def label(p):
            navn = getattr(p, "navn", None) or getattr(p, "poststed", None) or ""
            return f"{p.nummer} – {navn}" if navn else p.nummer

        options = "".join(f'<option value="{p.nummer}">{label(p)}</option>' for p in qs[:1000])
        return HttpResponse(options or '<option value="">(Ingen postnummer)</option>')


@method_decorator(require_GET, name="dispatch")
class ApiPostnummer(View):
    def get(self, request):
        nr = (request.GET.get("nr") or "").strip().zfill(4)
        pn = Postnummer.objects.filter(nummer=nr).first()
        if not pn:
            return JsonResponse({"found": False})
        pk = pn.kommuner.filter(primar=True).select_related("kommune__fylke").first() \
             or pn.kommuner.select_related("kommune__fylke").first()
        if not pk:
            return JsonResponse({"found": True})
        k = pk.kommune
        return JsonResponse({
            "found": True,
            "kommune_id": k.id,
            "kommune_navn": k.navn,
            "kommune_nr": k.nummer,
            "fylke_id": k.fylke_id,
            "fylke_navn": k.fylke.navn,
        })


# -----------------------
# Godkjenning (pending)
# -----------------------

class ApprovePermissionMixin(UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        return u.is_superuser or u.is_staff or u.has_perm("members.approve_member")


class PendingList(LoginRequiredMixin, ApprovePermissionMixin, ListView):
    model = Medlem
    template_name = "members/pending.html"
    context_object_name = "pendings"
    paginate_by = 50

    def get_queryset(self):
        return pending_qs().select_related("kommune", "kommune__fylke").order_by("etternavn", "fornavn")

class MemberApprove(LoginRequiredMixin, ApprovePermissionMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        m = get_object_or_404(Medlem, pk=pk)

        # Kun godkjenn “ekte pending”
        if (
            m.verve_kilde == "self"
            and m.verver_user_id is None
            and not (m.verver_navn or "").strip()
        ):
            display = request.user.get_full_name() or request.user.get_username()
            # Behold verve_kilde='self', sett hvem som godkjente
            m.verver_user = request.user
            if not (m.verver_navn or "").strip():
                m.verver_navn = display
            m.save(update_fields=["verver_user", "verver_navn"])
            messages.success(request, f"{m.fornavn} {m.etternavn} er godkjent.")
        else:
            messages.info(request, "Denne posten er ikke i 'til godkjenning'.")

        nxt = request.POST.get("next")
        if nxt:
            return redirect(nxt)
        return redirect(reverse("members:detail", kwargs={"pk": m.pk}))


class ApproveBulk(LoginRequiredMixin, ApprovePermissionMixin, View):
    http_method_names = ["post"]

    def post(self, request):
        ids = [int(x) for x in request.POST.getlist("ids") if str(x).isdigit()]
        if not ids:
            messages.info(request, "Ingen valgt.")
            return redirect(reverse("members:pending"))

        qs = pending_qs(Medlem.objects.filter(pk__in=ids))
        count = 0
        display = request.user.get_full_name() or request.user.get_username()

        for m in qs:
            # Behold verve_kilde='self', sett hvem som godkjente
            m.verver_user = request.user
            if not (m.verver_navn or "").strip():
                m.verver_navn = display
            m.save(update_fields=["verver_user", "verver_navn"])
            count += 1

        messages.success(request, f"Godkjente {count} selvregistrering(er).")
        return redirect(reverse("members:pending"))

