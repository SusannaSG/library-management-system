from django import forms

from .models import Book, Member


class IssueForm(forms.Form):
    member = forms.ModelChoiceField(
        queryset=Member.objects.all(), widget=forms.Select(attrs={"class": "form-select"})
    )
    book = forms.ModelChoiceField(
        queryset=Book.objects.all(), widget=forms.Select(attrs={"class": "form-select"})
    )
