import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from mailings.models import Outbox, EmailLog
from mailings.services import render_template, send_one

BATCH_SIZE = int(getattr(settings, "MAILINGS_BATCH_SIZE", 200))
MAX_PER_MIN = int(getattr(settings, "MAILINGS_MAX_PER_MINUTE", 120))

class Command(BaseCommand):
    help = "Sender e-post fra Outbox i batches"

    def add_arguments(self, parser):
        parser.add_argument("--campaign-id", type=int, help="Begrens til én kampanje")
        parser.add_argument("--dry-run", action="store_true", help="Ikke send, bare logg")

    def handle(self, *args, **opts):
        campaign_id = opts.get("campaign_id")
        dry = opts.get("dry_run", False)

        qs = Outbox.objects.filter(sent_ok=False).order_by("created")
        if campaign_id:
            qs = qs.filter(campaign_id=campaign_id)

        count = 0
        start = time.time()
        self.stdout.write(self.style.NOTICE(f"Starter sending (batch={BATCH_SIZE}, max/min={MAX_PER_MIN})"))
        while True:
            batch = list(qs.select_related("campaign", "campaign__template")[:BATCH_SIZE])
            if not batch:
                break

            # én SMTP-tilkobling per batch
            from django.core.mail import get_connection
            connection = get_connection()
            connection.open()
            try:
                for ob in batch:
                    t0 = time.time()
                    try:
                        ctx = {
                            "user": ob.campaign.opprettet_av,
                            "campaign": ob.campaign,
                            "medlem": None,  # senere: faktisk medlem
                        }
                        subject, text, html = render_template(ob.campaign.template, ctx)
                        if dry:
                            EmailLog.objects.create(outbox=ob, level="INFO", message=f"[DRY] Ville sendt til {ob.to_email}: {subject}")
                        else:
                            send_one(ob.to_email, subject, text, html, connection=connection)
                            ob.sent_ok = True
                        ob.attempts += 1
                        ob.last_try = timezone.now()
                        ob.save(update_fields=["sent_ok", "attempts", "last_try"])
                        EmailLog.objects.create(outbox=ob, level="INFO", message="Sendt OK" if not dry else "DRY OK")
                        count += 1
                    except Exception as e:
                        EmailLog.objects.create(outbox=ob, level="ERR", message=str(e))
                        ob.attempts += 1
                        ob.last_try = timezone.now()
                        ob.save(update_fields=["attempts", "last_try"])

                    # struping for å holde oss under MAX_PER_MIN
                    elapsed = time.time() - t0
                    min_interval = 60.0 / MAX_PER_MIN if MAX_PER_MIN > 0 else 0
                    if elapsed < min_interval:
                        time.sleep(min_interval - elapsed)
            finally:
                connection.close()

        dur = time.time() - start
        self.stdout.write(self.style.SUCCESS(f"Ferdig: {count} forsøk på {dur:.1f}s"))
