from django.shortcuts import render

# Create your views here.
# portal/views.py
from django.views.generic import TemplateView

class SentralDashboard(TemplateView):
    template_name = "portal/sentral.html"

class FylkeDashboard(TemplateView):
    template_name = "portal/fylke.html"

class LokallagDashboard(TemplateView):
    template_name = "portal/lokal.html"
