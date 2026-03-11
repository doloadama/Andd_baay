from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from baay.models import Projet, ProduitAgricole, Investissement, Localite, Profile, ProjetProduit


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
        initial='en_cours',
    )
    
    # Multiple products selection
    produits_selection = forms.ModelMultipleChoiceField(
        queryset=ProduitAgricole.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Produits cultives"
    )

    class Meta:
        model = Projet
        fields = ['nom', 'localite', 'superficie', 'date_lancement', 'rendement_estime', 'statut']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'localite': forms.Select(attrs={'class': 'form-control'}),
            'superficie': forms.NumberInput(attrs={'class': 'form-control'}),
            'date_lancement': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'rendement_estime': forms.NumberInput(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Afficher les noms des localites dans le formulaire
        self.fields['localite'].queryset = Localite.objects.all()
        self.fields['localite'].label_from_instance = lambda obj: obj.nom
        
        # Pre-select products if editing existing project
        if self.instance and self.instance.pk:
            self.fields['produits_selection'].initial = self.instance.projet_produits.values_list('produit_id', flat=True)

    def clean_superficie(self):
        superficie = self.cleaned_data['superficie']
        if superficie <= 0:
            raise forms.ValidationError("La superficie doit etre positive.")
        return superficie
    
    def clean(self):
        cleaned_data = super().clean()
        produits = cleaned_data.get('produits_selection')
        if not produits or len(produits) == 0:
            raise forms.ValidationError("Vous devez selectionner au moins un produit.")
        return cleaned_data


class ProjetProduitForm(forms.ModelForm):
    """Form for editing product details within a project (sowing and harvest data)"""
    
    class Meta:
        model = ProjetProduit
        fields = ['quantite_semences', 'superficie_allouee', 'date_semis', 
                  'date_recolte_prevue', 'date_recolte_effective', 'rendement_final', 'notes']
        widgets = {
            'quantite_semences': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Quantite en kg',
                'step': '0.01'
            }),
            'superficie_allouee': forms.NumberInput(attrs={
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
            'rendement_final': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Rendement final en kg',
                'step': '0.01'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Notes et observations...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_recolte_prevue'].required = False
        self.fields['date_recolte_effective'].required = False
        self.fields['rendement_final'].required = False
        self.fields['quantite_semences'].required = False
        self.fields['superficie_allouee'].required = False
        self.fields['date_semis'].required = False
        self.fields['notes'].required = False
    
    def clean_quantite_semences(self):
        quantite = self.cleaned_data.get('quantite_semences')
        if quantite is not None and quantite <= 0:
            raise forms.ValidationError("La quantite de semences doit etre positive.")
        return quantite
    
    def clean_superficie_allouee(self):
        superficie = self.cleaned_data.get('superficie_allouee')
        if superficie is not None and superficie <= 0:
            raise forms.ValidationError("La superficie allouee doit etre positive.")
        return superficie
    
    def clean(self):
        cleaned_data = super().clean()
        date_semis = cleaned_data.get('date_semis')
        date_recolte_prevue = cleaned_data.get('date_recolte_prevue')
        
        if date_semis and date_recolte_prevue and date_recolte_prevue < date_semis:
            raise forms.ValidationError(
                "La date de recolte prevue ne peut pas etre anterieure a la date de semis."
            )
        
        return cleaned_data


class RendementFinalForm(forms.Form):
    """Form for inputting final harvest yields when project is finished"""
    
    def __init__(self, *args, projet=None, **kwargs):
        super().__init__(*args, **kwargs)
        if projet:
            for pp in projet.projet_produits.all():
                self.fields[f'rendement_{pp.id}'] = forms.DecimalField(
                    label=f"Rendement final - {pp.produit.nom}",
                    max_digits=10,
                    decimal_places=2,
                    required=False,
                    initial=pp.rendement_final,
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control',
                        'placeholder': 'Quantite recoltee en kg',
                        'step': '0.01'
                    })
                )
                self.fields[f'date_recolte_{pp.id}'] = forms.DateField(
                    label=f"Date de recolte - {pp.produit.nom}",
                    required=False,
                    initial=pp.date_recolte_effective,
                    widget=forms.DateInput(attrs={
                        'type': 'date',
                        'class': 'form-control'
                    })
                )
