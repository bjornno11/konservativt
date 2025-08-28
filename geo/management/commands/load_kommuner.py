# geo/management/commands/load_kommuner.py
import csv, io
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date
from geo.models import Fylke, Kommune

def read_csv_any(path: Path):
    raw = path.read_bytes()
    text = None
    last_exc = None
    used_enc = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            text = raw.decode(enc)
            used_enc = enc
            break
        except UnicodeDecodeError as e:
            last_exc = e
    if text is None:
        raise CommandError(f"Klarte ikke å dekode {path} som UTF-8/cp1252/latin1: {last_exc}")

    header = text.splitlines()[0] if text else ""
    if "\t" in header:
        delim = "\t"
    elif ";" in header:
        delim = ";"
    else:
        try:
            dialect = csv.Sniffer().sniff(text[:2000])
            delim = dialect.delimiter
        except Exception:
            delim = ","
    return csv.DictReader(io.StringIO(text), delimiter=delim), used_enc, delim

class Command(BaseCommand):
    help = "Importer fylker og kommuner fra SSB KLASS CSV (to filer)."

    def add_arguments(self, parser):
        parser.add_argument("--fylker", required=True, help="CSV fra KLASS Fylkesinndeling (104)")
        parser.add_argument("--kommuner", required=True, help="CSV fra KLASS Kommuneinndeling (131)")

    def handle(self, *args, **opts):
        fylker_csv = Path(opts["fylker"])
        kommuner_csv = Path(opts["kommuner"])
        if not fylker_csv.exists() or not kommuner_csv.exists():
            raise CommandError("Fant ikke angitt CSV-fil.")

        # Fylker
        reader, enc_f, delim_f = read_csv_any(fylker_csv)
        f_cnt = 0
        for r in reader:
            code = (r.get("code") or r.get("Kode") or r.get("kode") or "").strip()
            name = (r.get("name") or r.get("Navn") or r.get("navn") or "").strip()
            vf   = (r.get("validFrom") or r.get("gyldigFom") or r.get("gyldig_fra") or "").strip()
            vt   = (r.get("validTo") or r.get("gyldigTom") or r.get("gyldig_til") or "").strip()
            if not code or not name:
                continue
            Fylke.objects.update_or_create(
                nummer=code.zfill(2),
                defaults={
                    "navn": name,
                    "gyldig_fra": parse_date(vf) if vf else None,
                    "gyldig_til": parse_date(vt) if vt else None,
                },
            )
            f_cnt += 1

        # Kommuner
        reader, enc_k, delim_k = read_csv_any(kommuner_csv)
        k_cnt = 0
        for r in reader:
            code = (r.get("code") or r.get("Kode") or r.get("kode") or "").strip()
            name = (r.get("name") or r.get("Navn") or r.get("navn") or "").strip()
            vf   = (r.get("validFrom") or r.get("gyldigFom") or r.get("gyldig_fra") or "").strip()
            vt   = (r.get("validTo") or r.get("gyldigTom") or r.get("gyldig_til") or "").strip()
            if not code or not name:
                continue
            fylkesnr = code[:2].zfill(2)
            try:
                fylke = Fylke.objects.get(nummer=fylkesnr)
            except Fylke.DoesNotExist:
                self.stderr.write(f"Advarsel: mangler fylke {fylkesnr} for kommune {code} {name}")
                continue
            Kommune.objects.update_or_create(
                nummer=code.zfill(4),
                defaults={
                    "navn": name,
                    "fylke": fylke,
                    "gyldig_fra": parse_date(vf) if vf else None,
                    "gyldig_til": parse_date(vt) if vt else None,
                    "aktiv": not bool(vt),
                },
            )
            k_cnt += 1

        self.stdout.write(self.style.SUCCESS(
            f"Fylker: {f_cnt} (enc={enc_f}, delim={'TAB' if delim_f=='\\t' else delim_f}) | "
            f"Kommuner: {k_cnt} (enc={enc_k}, delim={'TAB' if delim_k=='\\t' else delim_k})"
        ))
