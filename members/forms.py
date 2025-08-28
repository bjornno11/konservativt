from django import forms
from django.db import transaction
from .models import Medlem, Lokallag
from geo.models import Fylke, Kommune, Postnummer


class MedlemForm(forms.ModelForm):
    # Ekstra felt til UI
    fylke = forms.ModelChoiceField(
        queryset=Fylke.objects.order_by("navn"),
        required=False,
        label="Fylke",
    )
    postnr = forms.CharField(label="Postnummer", max_length=4, required=True)

    # Flere lokallag kan velges
    lokallag = forms.ModelMultipleChoiceField(
        queryset=Lokallag.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 8}),
        label="Lokallag",
    )

    class Meta:
        model = Medlem
        fields = [
            "fylke", "kommune", "lokallag",
            "fornavn", "etternavn", "adresse", "postnr", "telefon",
            "fodselsdato", "epost",
            "verve_kilde", "verver_navn",
        ]
        widgets = {"fodselsdato": forms.DateInput(attrs={"type": "date"})}

    # ----- init -----
    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

        # Påkrevde felt i din flyt
        self.fields["fornavn"].required = True
        self.fields["etternavn"].required = True
        self.fields["telefon"].required = True

        # Når bruker er innlogget: skjul vervefelter og sett fornuftige initialer
        if self.request and getattr(self.request, "user", None) and self.request.user.is_authenticated:
            self.fields["verve_kilde"].widget = forms.HiddenInput()
            self.fields["verver_navn"].widget = forms.HiddenInput()
            display = (getattr(self.request.user, "get_full_name", lambda: "")() or self.request.user.get_username())
            self.initial.setdefault("verve_kilde", "verver")
            self.initial.setdefault("verver_navn", display)
        else:
            # senere for selvregistrering
            self.initial.setdefault("verve_kilde", "self")

        # Filtrer kommune/lokallag etter valgt fylke
        fylke_id = (self.data.get("fylke") or self.initial.get("fylke")) or None
        if fylke_id:
            self.fields["kommune"].queryset = Kommune.objects.filter(fylke_id=fylke_id).order_by("navn")
            self.fields["lokallag"].queryset = Lokallag.objects.filter(fylke_id=fylke_id).order_by("navn")
        else:
            self.fields["kommune"].queryset = Kommune.objects.none()
            self.fields["lokallag"].queryset = Lokallag.objects.none()

        # Ytterligere snevring lokallag etter valgt kommune
        kommune_id = self.data.get("kommune") or self.initial.get("kommune")
        if kommune_id:
            self.fields["lokallag"].queryset = self.fields["lokallag"].queryset.filter(kommune_id=kommune_id)

        # Sørg for at postede lag-id’er er gyldige i queryset (unngå “invalid_choice”)
        posted_ids = []
        if hasattr(self.data, "getlist"):
            posted_ids = [x for x in self.data.getlist("lokallag") if str(x).isdigit()]
        if posted_ids:
            current_ids = list(self.fields["lokallag"].queryset.values_list("id", flat=True))
            allow_ids = set(current_ids) | {int(x) for x in posted_ids}
            self.fields["lokallag"].queryset = Lokallag.objects.filter(id__in=allow_ids)

        # interne flagg
        self._dupe_phones = 0
        self._postnummer_instance = None

    # ----- validering -----
    def clean_postnr(self):
        raw = (self.cleaned_data.get("postnr") or "").strip()
        if not raw.isdigit() or len(raw) != 4:
            raise forms.ValidationError("Ugyldig postnummer.")
        nr = raw.zfill(4)
        pn = Postnummer.objects.filter(nummer=nr).first()
        if not pn:
            raise forms.ValidationError("Postnummer finnes ikke i registeret.")
        self._postnummer_instance = pn
        return nr

    def clean(self):
        cleaned = super().clean()

        # Varsle (ikke blokkere) duplikat telefon
        tel = cleaned.get("telefon")
        if tel:
            qs = Medlem.objects.filter(telefon=tel)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            self._dupe_phones = qs.count()

        # Autofyll kommune/fylke fra postnummer
        pn = getattr(self, "_postnummer_instance", None)
        if pn:
            pk = pn.kommuner.filter(primar=True).select_related("kommune__fylke").first() \
                 or pn.kommuner.select_related("kommune__fylke").first()
            if pk:
                k = pk.kommune
                if not cleaned.get("kommune"):
                    cleaned["kommune"] = k
                if not cleaned.get("fylke"):
                    cleaned["fylke"] = k.fylke
                elif cleaned["fylke"] != k.fylke:
                    cleaned["fylke"] = k.fylke

        # Hvis verver-flyt (innlogget): sørg for et navn
        vk = (cleaned.get("verve_kilde") or "").lower()
        if vk.startswith("verv") and not cleaned.get("verver_navn"):
            if self.request and getattr(self.request, "user", None) and self.request.user.is_authenticated:
                display = (getattr(self.request.user, "get_full_name", lambda: "")() or self.request.user.get_username())
                cleaned["verver_navn"] = display
            else:
                self.add_error("verver_navn", "Oppgi navn på verver.")
        return cleaned

    # ----- lagring -----
    @transaction.atomic
    def save(self, request=None, commit=True):
        medlem = super().save(commit=False)

        # Knytt postnummer + evt. automatisk kommune
        pn = getattr(self, "_postnummer_instance", None)
        if pn is not None:
            medlem.postnummer = pn
            if not medlem.kommune:
                pk = pn.kommuner.filter(primar=True).select_related("kommune").first() \
                     or pn.kommuner.select_related("kommune").first()
                if pk:
                    medlem.kommune = pk.kommune

        # Sett verver automatisk når bruker er innlogget
        req = request or getattr(self, "request", None)
        if req and getattr(req, "user", None) and req.user.is_authenticated:
            medlem.verve_kilde = "verver"
            if hasattr(medlem, "verver_user"):
                medlem.verver_user = req.user
            if not getattr(medlem, "verver_navn", ""):
                display = (getattr(req.user, "get_full_name", lambda: "")() or req.user.get_username())
                medlem.verver_navn = display
        else:
            # senere for selvregistrering
            if not getattr(medlem, "verve_kilde", ""):
                medlem.verve_kilde = "self"

        if commit:
            medlem.save()
            # M2M (via through) styres av viewet (belte+seler). Ingen save_m2m her.
        return medlem

    @property
    def duplicate_phone_count(self):
        return self._dupe_phones

class SelfMedlemPublicForm(MedlemForm):
    """
    Offentlig (ikke-innlogget) registrering:
    - tvinger verve_kilde='self', verver_user=None, verver_navn=''
    - inkluderer et honeypot-felt for enkel bot-beskyttelse
    """
    hp_website = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta(MedlemForm.Meta):
        # samme felt som MedlemForm, men uten verve-feltene
        fields = [
            "fylke", "kommune", "lokallag",
            "fornavn", "etternavn", "adresse", "postnr", "telefon",
            "fodselsdato", "epost",
        ]

    def clean(self):
        cleaned = super().clean()
        # Honeypot: hvis utfylt -> avvis
        if cleaned.get("hp_website"):
            raise forms.ValidationError("Ugyldig innsending.")
        return cleaned

    def save(self, request=None, commit=True):
        # Passerer alltid request=None, så ikke forelder prøver å sette verver_user
        medlem = super().save(request=None, commit=False)
        medlem.verve_kilde = "self"
        medlem.verver_user = None
        medlem.verver_navn = ""
        if commit:
            medlem.save()
            # M2M (lokallag)
            self.save_m2m()
        else:
            self._save_m2m = self.save_m2m
        return medlem
