# myapp/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from baay.models import Projet, ProduitAgricole, Investissement, Localite


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


# myapp/forms.py
from django import forms
from .models import Investissement, Localite

class InvestissementForm(forms.ModelForm):
    class Meta:
        model = Investissement
        fields = ['description', 'cout_par_hectare', 'date_investissement']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'cout_par_hectare': forms.NumberInput(attrs={'class': 'form-control'}),
            'date_investissement': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, projet=None, **kwargs):
        super().__init__(*args, **kwargs)
        if projet:
            self.projet = projet

    def clean_cout_par_hectare(self):
        cout_par_hectare = self.cleaned_data.get('cout_par_hectare')
        if cout_par_hectare is not None and cout_par_hectare <= 0:
            raise forms.ValidationError("Le coût par hectare doit être positif.")
        return cout_par_hectare

class ProjetForm(forms.ModelForm):
    statut = forms.ChoiceField(
        choices=Projet.STATUT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='en_cours',  # Valeur par défaut
    )

    class Meta:
        model = Projet
        fields = ['nom','localite', 'culture', 'superficie', 'date_lancement', 'rendement_estime', 'statut']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'localite': forms.Select(attrs={'class': 'form-control'}),
            'culture': forms.Select(attrs={'class': 'form-control'}),
            'superficie': forms.NumberInput(attrs={'class': 'form-control'}),
            'date_lancement': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'rendement_estime': forms.NumberInput(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),  # Ajoute une classe CSS
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Afficher les noms des cultures dans le formulaire
        self.fields['culture'].queryset = ProduitAgricole.objects.all()
        self.fields['culture'].label_from_instance = lambda obj: obj.nom  # Afficher le nom au lieu de l'ID

        # Afficher les noms des cultures dans le formulaire
        self.fields['localite'].queryset = Localite.objects.all()
        self.fields['localite'].label_from_instance = lambda obj: obj.nom  # Afficher le nom au lieu de l'ID


    def clean_superficie(self):
        superficie = self.cleaned_data['superficie']
        if superficie <= 0:
            raise forms.ValidationError("La superficie doit être positive.")
        return superficie