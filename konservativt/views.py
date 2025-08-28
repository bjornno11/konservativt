# konservativt/views.py
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.views import LoginView
from django.urls import reverse

class Home(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("docs:docs-list")  # innloggede -> dokumenter
        return render(request, "welcome.html")  # utloggede -> velkommen

class MyLoginView(LoginView):
    redirect_authenticated_user = True

    def get_success_url(self):
        # 1) Respekter ?next=...
        url = self.get_redirect_url()
        if url:
            return url
        # 2) Ellers: staff/superuser -> admin, andre -> dokumentliste
        u = self.request.user
        if u.is_staff or u.is_superuser:
            return reverse("admin:index")        # /konservativt/admin/
        return reverse("docs:docs-list")         # /konservativt/doc/
