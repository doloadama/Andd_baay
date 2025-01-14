# myapp/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from baay.models import Projet, Culture, Investissement


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(max_length=30, required=True, label="Prénom")
    last_name = forms.CharField(max_length=30, required=True, label="Nom")
    phone_number = forms.CharField(max_length=15, required=True, label="Numéro de téléphone")

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "phone_number", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user

class ProjetForm(forms.ModelForm):
    class Meta:
        model = Projet
        fields = ['culture', 'investissement', 'superficie', 'date_lancement']
        widgets = {
            'date_lancement': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personnalisez les champs si nécessaire
        self.fields['culture'].queryset = Culture.objects.all()
        self.fields['investissement'].queryset = Investissement.objects.all()