# templates/import_medlemmer.py
import csv
import re
from django.utils import timezone
from django.apps import apps
from members.models import Medlem
from geo.models import Postnummer

# ---- KONFIG ----
ENCODING = "utf-8"          # bytt til "cp1252" om tegn ser feil ut
CSV_PATH = "medlemmer.csv"  # ved siden av manage.py
UPDATE_EXISTING = True      # oppdater eksisterende poster (på epost-match)
DUMMY_DOMAIN = "mangler.q1.no"

def normalize_key(k: str) -> str:
    k0 = (k or "").strip().lower()
    k1 = re.sub(r"[ \-_.]", "", k0)
    aliases = {
        "navn": "navn",
        "epost": "epost", "e-post": "epost", "email": "epost", "epostadresse": "epost",
        "tlf": "telefon", "telefon": "telefon", "tlfnr": "telefon", "mobil": "telefon",
        "adresse": "adresse",
        "postnr": "postnummer", "postnummer": "postnummer",
        "poststed": "poststed",
        "fylke": "fylke",
        "kommune": "kommune",
    }
    return aliases.get(k1, k1)

def split_name(fullname: str):
    parts = (fullname or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]

def sniff_dialect(path: str):
    with open(path, "r", encoding=ENCODING, errors="replace") as f:
        sample = f.read(4096)
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,")
    except Exception:
        class D(csv.excel):
            delimiter = ";"
        return D()

def unique_dummy_email(fornavn, etternavn, postnr):
    base = (etternavn or fornavn or "ukjent").strip().lower()
    base = re.sub(r"[^a-z0-9]+", ".", base).strip(".")
    return f"{base}.{postnr}@{DUMMY_DOMAIN}"

from django.apps import apps
from django.db.models.fields.related import ManyToManyField, ForeignKey

def get_kommune_from_postnummer(p, kommune_csv: str = ""):
    """
    Returner en geo.Kommune-instans for gitt Postnummer p.
    Prøver:
      (1) M2M Postnummer->Kommune
      (2) FK Kommune->Postnummer
      (3) Through-modell geo.PostnummerKommune (hvis finnes)
    Velger eksakt navnsmatch om oppgitt i CSV, ellers første.
    """
    Kommune = apps.get_model("geo", "Kommune")
    Postnummer = apps.get_model("geo", "Postnummer")

    kandidater = []

    # --- (1) M2M fra Postnummer til Kommune ---
    m2m_fields = [f for f in Postnummer._meta.get_fields() if isinstance(getattr(f, "remote_field", None), type(getattr(Postnummer._meta, "many_to_many", []))) or isinstance(f, ManyToManyField)]
    # Fall-back måte å finne M2M på:
    if not m2m_fields:
        m2m_fields = list(Postnummer._meta.many_to_many)

    for f in m2m_fields:
        rel_model = getattr(f.remote_field, "model", None)
        if rel_model is Kommune:
            # Fins det en M2M-manager på instansen?
            manager = getattr(p, f.name, None)
            try:
                if manager is not None:
                    kandidater = list(manager.all())
                else:
                    kandidater = []
            except Exception:
                kandidater = []
            if kandidater:
                break  # fant kommuner via M2M

    # --- (2) FK fra Kommune til Postnummer (reverse) ---
    if not kandidater:
        # Finn FK-felt i Kommune som peker til Postnummer
        fk_fields = [f for f in Kommune._meta.get_fields() if isinstance(f, ForeignKey) and getattr(f.remote_field, "model", None) is Postnummer]
        for fk in fk_fields:
            try:
                kandidater = list(Kommune.objects.filter(**{fk.name: p}))
            except Exception:
                kandidater = []
            if kandidater:
                break

    # --- (3) Through-modell geo.PostnummerKommune ---
    if not kandidater:
        try:
            Through = apps.get_model("geo", "PostnummerKommune")
        except LookupError:
            Through = None
        if Through is not None:
            # Finn FK-navn i through som peker til Postnummer og Kommune
            fk_post, fk_komm = None, None
            for f in Through._meta.get_fields():
                remote = getattr(f, "remote_field", None)
                if not remote:
                    continue
                if remote.model is Postnummer:
                    fk_post = f.name
                elif remote.model is Kommune:
                    fk_komm = f.name
            if fk_post and fk_komm:
                links = (Through.objects
                         .filter(**{f"{fk_post}_id": p.pk})
                         .select_related(fk_komm))
                kandidater = [getattr(l, fk_komm, None) for l in links if getattr(l, fk_komm, None) is not None]

    if not kandidater:
        return None

    # Velg kandidat: eksakt navnsmatch hvis kommune_csv er gitt
    if kommune_csv:
        kcsv = kommune_csv.strip().lower()
        for k in kandidater:
            if getattr(k, "navn", "").strip().lower() == kcsv:
                return k

    return kandidater[0]


def run():
    dialect = sniff_dialect(CSV_PATH)
    print(f"Bruker delimiter: {repr(dialect.delimiter)}")

    try:
        f = open(CSV_PATH, newline="", encoding=ENCODING, errors="replace")
    except FileNotFoundError:
        print(f"Fant ikke filen: {CSV_PATH}. Legg den ved siden av manage.py.")
        return

    reader = csv.DictReader(f, dialect=dialect)
    if not reader.fieldnames:
        print("Fant ingen header i CSV.")
        f.close()
        return

    fields_norm = {normalize_key(k): k for k in reader.fieldnames if k is not None}
    required = ["navn", "epost", "telefon", "adresse", "postnummer"]
    missing = [r for r in required if r not in fields_norm]
    if missing:
        print("Mangler påkrevde kolonner (normalisert):", missing)
        print("Fant (normalisert):", sorted(fields_norm.keys()))
        print("Original header:", reader.fieldnames)
        f.close()
        return

    created = exists = updated = skipped = unknown_postnr = 0
    rows = 0

    for row in reader:
        rows += 1
        g = lambda key: (row.get(fields_norm[key]) or "").strip()

        navn = g("navn")
        epost_in = g("epost").lower()
        telefon = g("telefon")
        adresse = g("adresse")
        postnr = g("postnummer")
        kommune_csv = g("kommune") if "kommune" in fields_norm else ""

        # Postnummer
        try:
            p = Postnummer.objects.get(nummer=postnr)
        except Postnummer.DoesNotExist:
            print(f"⚠️  Fant ikke postnr {postnr} for {navn}, hopper over.")
            unknown_postnr += 1
            skipped += 1
            continue

        # Kommune (ekte Kommune-instans via through)
        kommune = get_kommune_from_postnummer(p, kommune_csv)

        fornavn, etternavn = split_name(navn)

        # Dummy-epost hvis mangler
        epost = epost_in or unique_dummy_email(fornavn, etternavn, postnr)

        defaults = {
            "fornavn": fornavn,
            "etternavn": etternavn,
            "telefon": telefon,
            "adresse": adresse,
            "registrert": timezone.now(),
        }
        if hasattr(Medlem, "verve_kilde"):
            defaults["verve_kilde"] = "self"
        if hasattr(Medlem, "postnummer"):
            defaults["postnummer"] = p
        if hasattr(Medlem, "kommune") and kommune is not None:
            defaults["kommune"] = kommune

        medlem, created_flag = Medlem.objects.get_or_create(epost=epost, defaults=defaults)
        if created_flag:
            created += 1
            print(f"✅ Opprettet: {fornavn} {etternavn} ({postnr}) epost={epost}")
        else:
            if UPDATE_EXISTING:
                changed = False
                for field, value in [
                    ("fornavn", fornavn),
                    ("etternavn", etternavn),
                    ("telefon", telefon),
                    ("adresse", adresse),
                ]:
                    if value and getattr(medlem, field, None) != value:
                        setattr(medlem, field, value)
                        changed = True

                if hasattr(Medlem, "postnummer") and getattr(medlem, "postnummer_id", None) is None:
                    medlem.postnummer = p
                    changed = True

                if hasattr(Medlem, "kommune") and kommune and getattr(medlem, "kommune_id", None) is None:
                    medlem.kommune = kommune
                    changed = True

                if hasattr(Medlem, "verve_kilde") and not getattr(medlem, "verve_kilde", None):
                    medlem.verve_kilde = "self"
                    changed = True

                if changed:
                    medlem.save()
                    updated += 1
                    print(f"🛠️  Oppdatert: {fornavn} {etternavn} ({postnr}) epost={epost}")
                else:
                    exists += 1
                    print(f"ℹ️  Eksisterer (ingen endring): {fornavn} {etternavn} ({postnr}) epost={epost}")
            else:
                exists += 1
                print(f"ℹ️  Eksisterer: {fornavn} {etternavn} ({postnr}) epost={epost}")

    f.close()
    print(f"\nFerdig. Rader: {rows}, opprettet: {created}, oppdatert: {updated}, eksisterte: {exists}, hoppet: {skipped}, ukjent postnr: {unknown_postnr}.")

# kjør automatisk når fila pipes inn i Django shell
run()
