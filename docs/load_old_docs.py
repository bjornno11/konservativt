import os, sys, django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))  # gjør /srv/konservativt importérbart

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "konservativt.settings")
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from docs.models import Dokument


MEDIA_DIR = BASE_DIR / "media" / "dokumenter"


def run():
    user = User.objects.filter(is_superuser=True).first()
    count = 0

    for root, _, files in os.walk(MEDIA_DIR):
        for f in files:
            full_path = Path(root) / f
            rel_path = full_path.relative_to(BASE_DIR)
            rel_path_str = str(rel_path).replace("\\", "/")

            if not Dokument.objects.filter(fil=rel_path_str).exists():
                Dokument.objects.create(
                    navn=f,
                    beskrivelse="Gjenopprettet fra backup",
                    fil=rel_path_str,
                    opplastet_av=user,
                    lagtype="sentral",
                    lag_id=0,
                    opprettet=timezone.now(),
                    endret=timezone.now(),
                )
                count += 1

    print(f"{count} dokumenter gjenopprettet fra {MEDIA_DIR}")
if __name__ == "__main__":
    run()
