from django import forms
from .models import Document

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["folder", "tittel", "fil", "merknad"]
        widgets = {
            "tittel": forms.TextInput(attrs={"placeholder": "Kort tittel"}),
            "fil": forms.ClearableFileInput(attrs={"accept": "*/*"}),  # snevr inn ved behov
            "merknad": forms.Textarea(attrs={"rows": 4, "placeholder": "Valgfri merknad"}),
        }
