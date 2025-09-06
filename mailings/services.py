from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template import engines
from django.utils.html import strip_tags

def render_template(template, context):
    dj = engines["django"]
    subject = dj.from_string(template.subject).render(context).strip()
    html = dj.from_string(template.html_body).render(context)
    text = template.text_body.strip() if template.text_body else strip_tags(html)
    return subject, text, html

def send_one(to_email, subject, text, html, *, from_email=None, connection=None):
    from_email = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@localhost")
    msg = EmailMultiAlternatives(subject, text, from_email, [to_email], connection=connection)
    if html:
        msg.attach_alternative(html, "text/html")
    # Valgfritt: List-Unsubscribe header
    # msg.extra_headers = {"List-Unsubscribe": "<mailto:no-reply@q1.no?subject=unsubscribe>"}
    msg.send(fail_silently=False)
