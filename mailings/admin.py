from django.contrib import admin, messages
from django.utils.safestring import mark_safe
from django.template import Context
from django.conf import settings
from .models import EmailTemplate, Campaign, Outbox, EmailLog
from .services import render_template, send_one

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("navn", "subject", "sist_endret")
    search_fields = ("navn", "subject")
    actions = ["send_test_til_meg", "forhandsvis_html"]

    @admin.action(description="Send TEST til meg")
    def send_test_til_meg(self, request, queryset):
        user_email = request.user.email
        if not user_email:
            self.message_user(request, "Din bruker mangler e-postadresse.", level=messages.ERROR)
            return
        sent = 0
        for tmpl in queryset:
            ctx = Context({"user": request.user, "campaign": None, "medlem": None})
            subject, text, html = render_template(tmpl, ctx)
            try:
                send_one(user_email, f"[TEST] {subject}", text, html)
                sent += 1
            except Exception as e:
                self.message_user(request, f"Feil ved sending: {e}", level=messages.ERROR)
        self.message_user(request, f"Sendte {sent} test-epost(er) til {user_email}", level=messages.SUCCESS)

    @admin.action(description="Forhåndsvis HTML i admin-melding")
    def forhandsvis_html(self, request, queryset):
        tmpl = queryset.first()
        if not tmpl:
            return
        ctx = Context({"user": request.user, "campaign": None, "medlem": None})
        _, _, html = render_template(tmpl, ctx)
        self.message_user(request, mark_safe(f"<div style='max-width:700px;border:1px solid #ddd;padding:8px'>{html}</div>"))

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("navn", "status", "opprettet_av", "opprettet")
    list_filter = ("status",)
    search_fields = ("navn",)
    actions = ["legg_i_ko_kun_meg", "tom_kø"]

    @admin.action(description="Legg i kø → KUN min e-post (test)")
    def legg_i_ko_kun_meg(self, request, queryset):
        created = 0
        for camp in queryset:
            to_email = request.user.email
            if not to_email:
                self.message_user(request, "Din bruker mangler e-postadresse.", level=messages.ERROR)
                continue
            outbox, made = Outbox.objects.get_or_create(campaign=camp, to_email=to_email)
            if made:
                created += 1
                camp.status = "QUEUED"
                camp.save(update_fields=["status"])
        self.message_user(request, f"La {created} mottaker(e) i kø (din adresse).", level=messages.SUCCESS)

    @admin.action(description="Tøm kø for valgt kampanje")
    def tom_kø(self, request, queryset):
        total = 0
        from django.db.models import Q
        for camp in queryset:
            count, _ = Outbox.objects.filter(Q(campaign=camp) & Q(sent_ok=False)).delete()
            total += count
            camp.status = "DRAFT"
            camp.save(update_fields=["status"])
        self.message_user(request, f"Slettet {total} usendte kø-rader.", level=messages.SUCCESS)

@admin.register(Outbox)
class OutboxAdmin(admin.ModelAdmin):
    list_display = ("campaign", "to_email", "sent_ok", "attempts", "last_try", "created")
    list_filter = ("sent_ok", "campaign")
    search_fields = ("to_email",)

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("outbox", "level", "message", "created")
    list_filter = ("level", "created")
    search_fields = ("message",)
