# docs/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.http import Http404, FileResponse
from django.shortcuts import render, get_object_or_404, redirect
from .models import Dokument, Mappe
from .permissions import user_has_doc_perm, user_has_folder_perm
from django.http import Http404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

class DocumentList(LoginRequiredMixin, ListView):
    model = Dokument
    template_name = "docs/list.html"
    context_object_name = "docs"
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        qs = (
            Document.objects
            .select_related("folder", "opprettet_av")
            .prefetch_related("folder__can_read", "folder__can_write")
            .order_by("-opprettet")
        )
        allowed_ids = [d.id for d in qs if user_has_doc_perm(user, d, "view")]
        return (
            Document.objects
            .filter(id__in=allowed_ids)
            .select_related("folder", "opprettet_av")
        )


class DocumentDetail(LoginRequiredMixin, DetailView):
    model = Dokument
    template_name = "docs/detail.html"
    context_object_name = "doc"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not user_has_doc_perm(self.request.user, obj, "view"):
            raise Http404()
        return obj

class DocumentCreate(LoginRequiredMixin, CreateView):
    model = Dokument
    fields = ["folder", "tittel", "fil", "merknad"]
    template_name = "docs/form.html"

    def dispatch(self, request, *args, **kwargs):
        folder_id = request.POST.get("folder") or request.GET.get("folder")
        if folder_id:
            folder = get_object_or_404(DocFolder, pk=folder_id)
            if not user_has_folder_perm(request.user, folder, "add"):
                raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        folder = form.cleaned_data["folder"]
        if not user_has_folder_perm(self.request.user, folder, "add"):
            raise Http404()
        form.instance.opprettet_av = self.request.user
        return super().form_valid(form)

class DocumentUpdate(LoginRequiredMixin, UpdateView):
    model = Dokument
    fields = ["folder", "tittel", "fil", "merknad"]
    template_name = "docs/form.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not user_has_doc_perm(self.request.user, obj, "edit"):
            raise Http404()
        return obj

class DocumentDelete(LoginRequiredMixin, DeleteView):
    model = Dokument
    template_name = "docs/delete.html"
    success_url = "/docs/"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not user_has_doc_perm(self.request.user, obj, "delete"):
            raise Http404()
        return obj

def download_document(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    if not user_has_doc_perm(request.user, doc, "view"):
        raise Http404()
    if not doc.fil:
        raise Http404()
    return FileResponse(
        doc.fil.open("rb"),
        as_attachment=False,
        filename=doc.fil.name.rsplit("/", 1)[-1],
    )
from django.shortcuts import redirect

def doc_home(request):
    # Send forsiden rett til dokumentlisten
    return redirect("docs-list")

@login_required
def doc_folder(request, folder_id: int):
    folder = get_object_or_404(DocFolder, pk=folder_id)

    # Sjekk mappe-tilgang (lese)
    if not user_has_folder_perm(request.user, folder, "view"):
        raise Http404()

    # Hent dokumenter i mappa som bruker faktisk kan se
    qs = (
        Document.objects.filter(folder=folder)
        .select_related("folder", "opprettet_av")
        .prefetch_related("folder__can_read", "folder__can_write")
        .order_by("-opprettet")
    )
    docs = [d for d in qs if user_has_doc_perm(request.user, d, "view")]

    # Gjenbruk liste-templaten; send med 'folder' for heading/lenker
    return render(request, "docs/list.html", {"docs": docs, "folder": folder})

@login_required
def doc_upload(request):
    # Bruker samme rettighetssjekk som i DocumentCreate.dispatch()
    return DocumentCreate.as_view()(request)

@login_required
def doc_download(request, doc_id: int):
    # videresender til den faktiske nedlastings-funksjonen
    return download_document(request, pk=doc_id)

