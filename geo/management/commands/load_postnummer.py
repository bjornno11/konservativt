import csv, io
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps

Postnummer = apps.get_model("geo", "Postnummer")
Kommune = apps.get_model("geo", "Kommune")
try:
    PostnummerKommune = apps.get_model("geo", "PostnummerKommune")
    HAS_PNK = True
except LookupError:
    PostnummerKommune = None
    HAS_PNK = False

def decode_best(path: Path):
    raw = path.read_bytes()
    last_exc = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError as e:
            last_exc = e
    raise CommandError(f"Klarte ikke å dekode {path} som UTF-8/cp1252/latin1: {last_exc}")

def pick_delimiter(text: str):
    header = text.splitlines()[0] if text else ""
    if "\t" in header: return "\t", "TAB"
    if ";" in header:  return ";",  ";"
    try:
        dialect = csv.Sniffer().sniff(text[:2000])
        return dialect.delimiter, dialect.delimiter
    except Exception:
        return ",", ","

class Command(BaseCommand):
    help = "Importer Postens/Bring postnummer (tåler ANSI/UTF-8; TSV/CSV; med/uten header)."

    def add_arguments(self, parser):
        parser.add_argument("--fil", required=True, help="Sti til filen (tsv/csv/txt)")
        parser.add_argument("--dry-run", action="store_true", help="Ikke skriv til DB – bare rapporter")

    def handle(self, *args, **opts):
        verbosity = int(opts.get("verbosity", 1))
        def vlog(msg):
            if verbosity >= 2:
                self.stdout.write(msg)

        p = Path(opts["fil"])
        if not p.exists():
            raise CommandError(f"Fant ikke fil: {p}")

        text, enc = decode_best(p)
        delim, delim_name = pick_delimiter(text)

        # Første forsøk: anta header
        reader = csv.DictReader(io.StringIO(text), delimiter=delim)
        fieldnames = [fn.strip() for fn in (reader.fieldnames or [])]

        # Hvis første linje ser ut som DATA (ikke header), sett felt manuelt
        expected = {"postnummer", "poststed", "kommunenummer", "kommunenavn", "kategori"}
        if not any(fn.lower() in expected for fn in fieldnames):
            manual_fields = ["Postnummer", "Poststed", "Kommunenummer", "Kommunenavn", "Kategori"]
            reader = csv.DictReader(io.StringIO(text), delimiter=delim, fieldnames=manual_fields)
            fieldnames = manual_fields
            vlog("Ingen gyldig header funnet – bruker manuelle felt: " + ", ".join(manual_fields))

        vlog(f"Felt i fil: {fieldnames}")

        # Hent felter fra dict uansett variant / case
        def g(d, *keys):
            for k in keys:
                if k in d: return d[k]
            lower = {k.lower(): v for k, v in d.items()}
            for k in keys:
                v = lower.get(k.lower())
                if v is not None: return v
            return ""

        has_kategori_field = "kategori" in {f.name for f in Postnummer._meta.get_fields()}

        n_rows = 0
        n_written = 0
        for r in reader:
            n_rows += 1
            nr   = (g(r, "postnummer", "Postnummer") or "").strip()
            sted = (g(r, "poststed", "Poststed") or "").strip().title()
            kat  = (g(r, "kategori", "Kategori") or "").strip()[:1].upper()
            k_nr = (g(r, "kommunenummer", "Kommunenummer") or "").strip()

            if not nr or not sted:
                continue

            defaults = {"poststed": sted}
            if has_kategori_field:
                defaults["kategori"] = kat or ""

            if not opts["dry_run"]:
                pn, _ = Postnummer.objects.update_or_create(
                    nummer=nr.zfill(4),
                    defaults=defaults,
                )
                if HAS_PNK and k_nr:
                    k = Kommune.objects.filter(nummer=k_nr.zfill(4)).first()
                    if k:
                        PostnummerKommune.objects.update_or_create(
                            postnummer=pn, kommune=k, defaults={"primar": True}
                        )
                n_written += 1

        self.stdout.write(self.style.SUCCESS(
            f"Lest {n_rows} rader | skrevet {n_written} | enc={enc} | delim={delim_name} | "
            f"PNK={'ja' if HAS_PNK else 'nei'}"
        ))
