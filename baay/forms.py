from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from baay.models import Projet, ProduitAgricole, Investissement, Localite, Profile, Semis


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


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prénom'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
        }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['phone_number', 'address']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro de téléphone (+221...)'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Adresse complète'}),
        }


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
            'statut': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Afficher les noms des cultures dans le formulaire
        self.fields['culture'].queryset = ProduitAgricole.objects.all()
        self.fields['culture'].label_from_instance = lambda obj: obj.nom

        # Afficher les noms des localités dans le formulaire
        self.fields['localite'].queryset = Localite.objects.all()
        self.fields['localite'].label_from_instance = lambda obj: obj.nom


    def clean_superficie(self):
        superficie = self.cleaned_data['superficie']
        if superficie <= 0:
            raise forms.ValidationError("La superficie doit être positive.")
        return superficie


class SemisForm(forms.ModelForm):
    """Form for creating and editing sowings"""
    
    class Meta:
        model = Semis
        fields = ['culture', 'projet', 'quantite_semences', 'superficie_semee', 
                  'date_semis', 'date_recolte_prevue', 'statut', 'notes', 
                  'date_recolte_effective', 'rendement_obtenu']
        widgets = {
            'culture': forms.Select(attrs={'class': 'form-control'}),
            'projet': forms.Select(attrs={'class': 'form-control'}),
            'quantite_semences': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Quantité en kg',
                'step': '0.01'
            }),
            'superficie_semee': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Superficie en hectares',
                'step': '0.01'
            }),
            'date_semis': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control'
            }),
            'date_recolte_prevue': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control'
            }),
            'date_recolte_effective': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control'
            }),
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Notes et observations sur ce semis...'
            }),
            'rendement_obtenu': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Rendement en kg',
                'step': '0.01'
            }),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['culture'].queryset = ProduitAgricole.objects.all()
        self.fields['culture'].label_from_instance = lambda obj: obj.nom
        
        # Filter projects by user if provided
        if user:
            self.fields['projet'].queryset = Projet.objects.filter(utilisateur=user.profile)
        else:
            self.fields['projet'].queryset = Projet.objects.none()
        
        self.fields['projet'].label_from_instance = lambda obj: obj.nom
        self.fields['projet'].required = False
        self.fields['date_recolte_prevue'].required = False
        self.fields['date_recolte_effective'].required = False
        self.fields['rendement_obtenu'].required = False
    
    def clean_quantite_semences(self):
        quantite = self.cleaned_data.get('quantite_semences')
        if quantite is not None and quantite <= 0:
            raise forms.ValidationError("La quantité de semences doit être positive.")
        return quantite
    
    def clean_superficie_semee(self):
        superficie = self.cleaned_data.get('superficie_semee')
        if superficie is not None and superficie <= 0:
            raise forms.ValidationError("La superficie semée doit être positive.")
        return superficie
    
    def clean(self):
        cleaned_data = super().clean()
        date_semis = cleaned_data.get('date_semis')
        date_recolte_prevue = cleaned_data.get('date_recolte_prevue')
        
        if date_semis and date_recolte_prevue and date_recolte_prevue < date_semis:
            raise forms.ValidationError(
                "La date de récolte prévue ne peut pas être antérieure à la date de semis."
            )
        
        return cleaned_data
