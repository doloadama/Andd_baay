from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
import json
from baay.models import (
    DemandeAccesFerme,
    Ferme,
    Investissement,
    Localite,
    Pays,
    ProduitAgricole,
    Profile,
    Projet,
    ProjetProduit,
    Recette,
    Region,
    Tache,
)
from baay.permissions import role_dans_ferme, roles_assignables_par


def _aligner_champ_categorie_investissement(form_field, *, instance):
    """
    Les deux formulaires (fiche projet + hub Finance) exposent la même liste
    que Investissement.CATEGORIE_CHOICES (seule définition métier).
    """
    form_field.choices = list(Investissement.CATEGORIE_CHOICES)
    form_field.label = "Catégorie"
    if not (instance and getattr(instance, "pk", None)):
        form_field.initial = Investissement.CATEGORIE_GENERAL


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    """Accepte l’adresse email (recommandé) ou le nom d’utilisateur Django pour la connexion."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Adresse email'
        self.fields['username'].widget.attrs.update(
            {
                'class': 'form-control',
                'placeholder': 'vous@exemple.com',
                'autocomplete': 'username',
            }
        )
        self.fields['password'].widget.attrs.update(
            {
                'class': 'form-control',
                'placeholder': '••••••••',
                'autocomplete': 'current-password',
            }
        )

    def clean_username(self):
        identifier = (self.cleaned_data.get('username') or '').strip()
        if '@' in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
            if user:
                return user.username
        return identifier


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(max_length=30, required=True, label="Prénom")
    last_name = forms.CharField(max_length=30, required=True, label="Nom")
    phone_indicatif = forms.CharField(max_length=6, required=True, label="Indicatif")
    phone_numero = forms.CharField(max_length=15, required=True, label="Numéro de téléphone")

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "phone_indicatif", "phone_numero", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Le username est généré automatiquement à partir du prénom et nom.
        if 'username' in self.fields:
            self.fields['username'].required = False
            self.fields['username'].widget = forms.HiddenInput()

    @staticmethod
    def _generate_username(first_name, last_name):
        from django.utils.text import slugify
        base = slugify(f"{first_name}.{last_name}") or "user"
        base = base[:140]
        candidate = base
        i = 1
        while User.objects.filter(username__iexact=candidate).exists():
            i += 1
            suffix = str(i)
            candidate = f"{base[:150 - len(suffix) - 1]}.{suffix}"
        return candidate

    def clean_phone_indicatif(self):
        val = (self.cleaned_data.get('phone_indicatif') or '').strip()
        if not val.startswith('+'):
            val = '+' + val.lstrip('+')
        if not val[1:].isdigit() or not (1 <= len(val[1:]) <= 4):
            raise forms.ValidationError("Indicatif invalide.")
        return val

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Un compte avec cet email existe déjà.")
        return email

    def clean_phone_numero(self):
        raw = (self.cleaned_data.get('phone_numero') or '').strip()
        digits = ''.join(ch for ch in raw if ch.isdigit())
        if not (6 <= len(digits) <= 12):
            raise forms.ValidationError("Le numéro doit contenir entre 6 et 12 chiffres.")
        return digits

    def clean(self):
        cleaned = super().clean()
        first_name = cleaned.get('first_name')
        last_name = cleaned.get('last_name')
        if first_name and last_name and not cleaned.get('username'):
            cleaned['username'] = self._generate_username(first_name, last_name)
            self.instance.username = cleaned['username']
        indicatif = cleaned.get('phone_indicatif')
        numero = cleaned.get('phone_numero')
        if indicatif and numero:
            full = f"{indicatif}{numero}"
            if len(full) > 15:
                self.add_error('phone_numero', "Le numéro complet (indicatif + numéro) ne peut pas dépasser 15 caractères.")
            else:
                cleaned['phone_number'] = full
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if not user.username:
            user.username = self._generate_username(user.first_name, user.last_name)
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
        fields = [
            "libelle",
            "categorie",
            "description",
            "cout_par_hectare",
            "autres_frais",
            "date_investissement",
            "projet_produit",
        ]
        widgets = {
            "libelle": forms.TextInput(
                attrs={
                    "class": "fh-field",
                    "id": "id_libelle",
                    "placeholder": "Ex. Achat d'engrais…",
                    "autocomplete": "off",
                }
            ),
            "categorie": forms.Select(attrs={"class": "fh-field", "id": "id_categorie"}),
            "description": forms.Textarea(
                attrs={
                    "class": "fh-field",
                    "id": "id_description",
                    "rows": 4,
                    "placeholder": "Détails, libellé long…",
                }
            ),
            "cout_par_hectare": forms.NumberInput(
                attrs={"class": "fh-field", "id": "id_cout_par_hectare", "step": "0.01", "min": "0"}
            ),
            "autres_frais": forms.NumberInput(
                attrs={"class": "fh-field", "id": "id_autres_frais", "step": "0.01", "min": "0"}
            ),
            "date_investissement": forms.DateInput(
                attrs={"type": "date", "class": "fh-field", "id": "id_date_investissement"}
            ),
            "projet_produit": forms.Select(attrs={"class": "fh-field", "id": "id_projet_produit"}),
        }

    def __init__(self, *args, projet=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.projet = projet
        self.fields["libelle"].required = False
        self.fields["description"].required = False
        self.fields["projet_produit"].required = False
        self.fields["autres_frais"].required = False
        _aligner_champ_categorie_investissement(self.fields["categorie"], instance=self.instance)
        if projet:
            self.fields["projet_produit"].queryset = (
                projet.projet_produits.select_related("produit").order_by("produit__nom")
            )
            self.fields["projet_produit"].label_from_instance = lambda p: p.produit.nom
        else:
            self.fields["projet_produit"].queryset = ProjetProduit.objects.none()

    def clean_cout_par_hectare(self):
        cout_par_hectare = self.cleaned_data.get("cout_par_hectare")
        if cout_par_hectare is not None and cout_par_hectare <= 0:
            raise forms.ValidationError("Le coût par hectare doit être positif.")
        return cout_par_hectare

    def clean(self):
        cleaned_data = super().clean()
        pp = cleaned_data.get("projet_produit")
        libelle = (cleaned_data.get("libelle") or "").strip()
        description = (cleaned_data.get("description") or "").strip()
        if not libelle and description:
            cleaned_data["libelle"] = description.split("\n")[0][:255]
        elif not libelle and not description:
            raise forms.ValidationError(
                {"description": "Indiquez un libellé ou une description."}
            )
        if self.projet and pp and pp.projet_id != self.projet.id:
            raise forms.ValidationError(
                {"projet_produit": "Cette culture n'appartient pas au projet."}
            )
        return cleaned_data


class FinanceDepenseForm(forms.ModelForm):
    """Saisie d'une dépense depuis le hub Finance (choix du projet)."""

    class Meta:
        model = Investissement
        fields = [
            "projet",
            "projet_produit",
            "libelle",
            "categorie",
            "description",
            "cout_par_hectare",
            "autres_frais",
            "date_investissement",
        ]
        widgets = {
            "projet": forms.Select(attrs={"class": "fh-field"}),
            "projet_produit": forms.Select(attrs={"class": "fh-field", "id": "id_projet_produit"}),
            "libelle": forms.TextInput(
                attrs={
                    "class": "fh-field",
                    "id": "fLibelle",
                    "placeholder": "Ex. Achat d'engrais, irrigation…",
                    "autocomplete": "off",
                }
            ),
            "categorie": forms.Select(attrs={"class": "fh-field", "id": "fCategorie"}),
            "description": forms.Textarea(
                attrs={
                    "class": "fh-field",
                    "id": "fDescription",
                    "rows": 4,
                    "placeholder": "Détails complémentaires…",
                }
            ),
            "cout_par_hectare": forms.NumberInput(
                attrs={"class": "fh-field", "id": "fCoutHa", "step": "0.01", "min": "0"}
            ),
            "autres_frais": forms.NumberInput(
                attrs={"class": "fh-field", "id": "fFraisAutres", "step": "0.01", "min": "0"}
            ),
            "date_investissement": forms.DateInput(
                attrs={"type": "date", "class": "fh-field", "id": "fDateInv"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        from django.urls import reverse

        from baay.permissions import projets_modifiables_depenses_qs

        if user and user.is_authenticated:
            self.fields["projet"].queryset = projets_modifiables_depenses_qs(user.profile).order_by(
                "nom"
            )
        self.fields["projet"].empty_label = "Choisir un projet…"
        self.fields["projet_produit"].required = False
        projet_pk = None
        if self.data.get("projet"):
            projet_pk = self.data.get("projet")
        elif getattr(self.instance, "pk", None) and getattr(self.instance, "projet_id", None):
            projet_pk = self.instance.projet_id
        if projet_pk:
            self.fields["projet_produit"].queryset = (
                ProjetProduit.objects.filter(projet_id=projet_pk)
                .select_related("produit")
                .order_by("produit__nom")
            )
        else:
            self.fields["projet_produit"].queryset = ProjetProduit.objects.none()
        self.fields["description"].required = False
        self.fields["libelle"].required = True
        self.fields["autres_frais"].required = False
        self.fields["projet"].widget.attrs.setdefault("id", "id_finance_depense_projet")
        self.fields["projet"].widget.attrs.update(
            {
                "hx-get": reverse("finance_produits_form_partial"),
                "hx-include": "this",
                "hx-target": "#finance-depense-produit-wrap",
                "hx-swap": "innerHTML",
                "hx-trigger": "change",
            }
        )
        self.fields["libelle"].label = "Libellé"
        _aligner_champ_categorie_investissement(self.fields["categorie"], instance=self.instance)
        self.fields["date_investissement"].label = "Date"
        self.fields["projet_produit"].label = "Culture"
        self.fields["cout_par_hectare"].label = "Coût / ha (FCFA)"
        self.fields["autres_frais"].label = "Autres frais (FCFA)"

    def clean_cout_par_hectare(self):
        cout = self.cleaned_data.get("cout_par_hectare")
        if cout is not None and cout <= 0:
            raise forms.ValidationError("Le coût par hectare doit être positif.")
        return cout

    def clean(self):
        cleaned_data = super().clean()
        projet = cleaned_data.get("projet")
        pp = cleaned_data.get("projet_produit")
        if projet and pp and pp.projet_id != projet.id:
            raise forms.ValidationError(
                {"projet_produit": "La culture ne correspond pas au projet sélectionné."}
            )
        return cleaned_data


class FinanceRecetteForm(forms.ModelForm):
    """Saisie d'une recette (vente) depuis le hub Finance."""

    class Meta:
        model = Recette
        fields = [
            "projet",
            "projet_produit",
            "produit",
            "quantite",
            "unite",
            "prix_unitaire",
            "date_vente",
        ]
        widgets = {
            "projet": forms.Select(attrs={"class": "fh-field"}),
            "projet_produit": forms.Select(attrs={"class": "fh-field"}),
            "produit": forms.TextInput(
                attrs={
                    "class": "fh-field",
                    "placeholder": "Ex. riz paddy (auto si culture choisie)",
                    "autocomplete": "off",
                }
            ),
            "quantite": forms.NumberInput(
                attrs={
                    "class": "fh-field",
                    "id": "fRecQty",
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "unite": forms.Select(attrs={"class": "fh-field"}),
            "prix_unitaire": forms.NumberInput(
                attrs={
                    "class": "fh-field",
                    "id": "fRecPrix",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "date_vente": forms.DateInput(
                attrs={"type": "date", "class": "fh-field", "id": "fDateVente"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        kwargs.setdefault("prefix", "recette")
        self.user = user
        super().__init__(*args, **kwargs)
        from django.urls import reverse

        from baay.permissions import projets_modifiables_depenses_qs

        if user and user.is_authenticated:
            self.fields["projet"].queryset = projets_modifiables_depenses_qs(user.profile).order_by(
                "nom"
            )
        self.fields["projet"].empty_label = "Choisir un projet…"
        self.fields["projet_produit"].required = False
        self.fields["produit"].required = False
        projet_key = f"{self.prefix}-projet" if self.prefix else "projet"
        projet_pk = None
        if self.data.get(projet_key):
            projet_pk = self.data.get(projet_key)
        elif getattr(self.instance, "pk", None) and getattr(self.instance, "projet_id", None):
            projet_pk = self.instance.projet_id
        if projet_pk:
            self.fields["projet_produit"].queryset = (
                ProjetProduit.objects.filter(projet_id=projet_pk)
                .select_related("produit")
                .order_by("produit__nom")
            )
        else:
            self.fields["projet_produit"].queryset = ProjetProduit.objects.none()

        pp_name = f"{self.prefix}-projet_produit" if self.prefix else "projet_produit"
        self.fields["projet_produit"].widget.attrs["id"] = f"id_{pp_name}"
        self.fields["projet"].widget.attrs["id"] = f"id_{self.prefix}-projet"

        self.fields["projet"].widget.attrs.update(
            {
                "hx-get": reverse("finance_produits_form_partial") + "?form=recette",
                "hx-include": "this",
                "hx-target": "#finance-recette-produit-wrap",
                "hx-swap": "innerHTML",
                "hx-trigger": "change",
            }
        )
        self.fields["projet"].label = "Projet"
        self.fields["projet_produit"].label = "Culture"
        self.fields["produit"].label = "Produit vendu"
        self.fields["quantite"].label = "Quantité"
        self.fields["unite"].label = "Unité"
        self.fields["prix_unitaire"].label = "Prix unitaire (FCFA)"
        self.fields["date_vente"].label = "Date de vente"

    def clean(self):
        cleaned_data = super().clean()
        projet = cleaned_data.get("projet")
        pp = cleaned_data.get("projet_produit")
        if projet and pp and pp.projet_id != projet.id:
            raise forms.ValidationError(
                {"projet_produit": "La culture ne correspond pas au projet sélectionné."}
            )
        return cleaned_data


class ProjetForm(forms.ModelForm):
    statut = forms.ChoiceField(
        choices=Projet.STATUT_CHOICES,
        widget=forms.Select(attrs={'class': 'fh-field'}),
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
        fields = [
            'nom',
            'ferme',
            'image_fond',
            'pays',
            'localite',
            'superficie',
            'date_lancement',
            'date_fin',
            'taux_avancement_personnalise',
            'rendement_estime',
            'budget_alloue',
            'statut',
            'type_irrigation',
            'type_engrais',
        ]
        labels = {
            'budget_alloue': 'Budget prévisionnel (FCFA)',
            'taux_avancement_personnalise': "Taux d'avancement personnalisé (%)",
        }
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'fh-field', 'placeholder': 'Ex. Rizière Nord 2024'}),
            'ferme': forms.Select(attrs={'class': 'fh-field'}),
            'image_fond': forms.ClearableFileInput(attrs={'class': 'fh-field', 'accept': 'image/*', 'capture': 'environment'}),
            'pays': forms.Select(attrs={'class': 'fh-field'}),
            'localite': forms.Select(attrs={'class': 'fh-field'}),
            'superficie': forms.NumberInput(attrs={'class': 'fh-field', 'step': '0.01', 'min': '0'}),
            'date_lancement': forms.DateInput(attrs={'type': 'date', 'class': 'fh-field'}),
            'date_fin': forms.DateInput(attrs={'type': 'date', 'class': 'fh-field'}),
            'taux_avancement_personnalise': forms.NumberInput(
                attrs={
                    'class': 'fh-field',
                    'min': 0,
                    'max': 100,
                    'step': 1,
                    'placeholder': 'Auto (selon les dates)',
                }
            ),
            'rendement_estime': forms.NumberInput(attrs={'class': 'fh-field', 'step': '0.01', 'min': '0'}),
            'budget_alloue': forms.NumberInput(
                attrs={'class': 'fh-field', 'step': '0.01', 'min': '0', 'placeholder': 'Optionnel (FCFA)'}
            ),
            'type_irrigation': forms.Select(attrs={'class': 'fh-field'}),
            'type_engrais': forms.Select(attrs={'class': 'fh-field'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        from_ferme = kwargs.pop("from_ferme", None)
        for_edit = kwargs.pop("for_edit", False)
        super().__init__(*args, **kwargs)
        if for_edit:
            self.fields.pop("type_irrigation", None)
            self.fields.pop("type_engrais", None)
        else:
            if "type_irrigation" in self.fields:
                self.fields["type_irrigation"].required = False
            if "type_engrais" in self.fields:
                self.fields["type_engrais"].required = False
        # La superficie globale peut etre calculee automatiquement a partir des
        # superficies par produit (mode "per-product"). On la rend optionnelle
        # ici et la validation finale se fait dans clean().
        if "superficie" in self.fields:
            self.fields["superficie"].required = False
        if 'pays' in self.fields:
            self.fields['pays'].queryset = Pays.objects.all().order_by('nom')
            self.fields['pays'].label_from_instance = lambda obj: obj.nom
        self.fields['localite'].queryset = Localite.objects.all().order_by('nom')
        self.fields['localite'].label_from_instance = lambda obj: obj.nom

        # Filter farms to user's own farms and farms they are members of
        if 'ferme' in self.fields and user:
            from django.db.models import Q
            from baay.models import Ferme
            self.fields['ferme'].queryset = Ferme.objects.filter(
                Q(proprietaire=user.profile) | Q(membres__utilisateur=user.profile)
            ).distinct().order_by('nom')
            self.fields['ferme'].label_from_instance = lambda obj: obj.nom
            self.fields['ferme'].required = True
        
        # When creating from a farm detail page, pre-fill and hide farm/location fields
        if from_ferme:
            self.fields['ferme'].widget = forms.HiddenInput()
            if from_ferme.pays:
                self.fields['pays'].widget = forms.HiddenInput()
            if from_ferme.localite:
                self.fields['localite'].widget = forms.HiddenInput()
        
        # Pré-sélection produits si édition
        if self.instance and self.instance.pk:
            self.fields['produits_selection'].initial = self.instance.projet_produits.values_list(
                'produit_id', flat=True
            )

        from baay.permissions import peut_personnaliser_taux_avancement_projet

        can_set_av = (
            user
            and user.is_authenticated
            and self.instance
            and getattr(self.instance, "pk", None)
            and getattr(self.instance, "ferme_id", None)
            and peut_personnaliser_taux_avancement_projet(user.profile, self.instance)
        )
        if not can_set_av:
            self.fields.pop('taux_avancement_personnalise', None)
        else:
            self.fields['taux_avancement_personnalise'].required = False
            self.fields['taux_avancement_personnalise'].help_text = (
                "Laisser vide pour calculer automatiquement à partir des dates de lancement et de fin. "
                "Réservé au manager de la ferme ou à l'administrateur."
            )

    def clean_superficie(self):
        superficie = self.cleaned_data.get('superficie')
        ferme = self.cleaned_data.get('ferme')
        if superficie is not None and superficie <= 0:
            raise forms.ValidationError("La superficie doit etre positive.")
        if superficie is not None and ferme and ferme.superficie_totale:
            if superficie > ferme.superficie_totale:
                raise forms.ValidationError(
                    f"La superficie du projet ({superficie} ha) ne peut pas dépasser celle de la ferme ({ferme.superficie_totale} ha)."
                )
        return superficie
    
    def clean(self):
        from decimal import Decimal, InvalidOperation
        from django.db.models import Sum
        cleaned_data = super().clean()
        produits = list(cleaned_data.get('produits_selection') or [])
        ferme = cleaned_data.get('ferme')
        date_lancement = cleaned_data.get('date_lancement')
        date_fin = cleaned_data.get('date_fin')
        if date_lancement and date_fin and date_fin <= date_lancement:
            self.add_error('date_fin', "La date de fin doit etre posterieure a la date de debut.")
        if not produits:
            raise forms.ValidationError("Vous devez selectionner au moins un produit.")

        # Mode "per-product" : si la requete contient au moins une superficie
        # par produit, on calcule la superficie totale a partir de la somme.
        per_product_keys = [f'superficie_{p.id}' for p in produits]
        per_product_present = any((self.data.get(k) or '').strip() for k in per_product_keys)

        if per_product_present:
            superficies = {}
            total = Decimal('0')
            errors = []
            for p in produits:
                raw = (self.data.get(f'superficie_{p.id}') or '').strip()
                if not raw:
                    errors.append(f"Superficie manquante pour {p.nom}.")
                    continue
                try:
                    val = Decimal(raw)
                except (InvalidOperation, ValueError):
                    errors.append(f"Superficie invalide pour {p.nom}.")
                    continue
                if val <= 0:
                    errors.append(f"La superficie pour {p.nom} doit etre positive.")
                    continue
                superficies[str(p.id)] = val
                total += val
            if errors:
                raise forms.ValidationError(errors)
            cleaned_data['superficies_par_produit'] = superficies
            cleaned_data['superficie'] = total
            superficie = total
        else:
            superficie = cleaned_data.get('superficie')
            if superficie is None:
                raise forms.ValidationError("La superficie est obligatoire.")
            if superficie <= 0:
                raise forms.ValidationError("La superficie doit etre positive.")

        # Validation contre la superficie totale de la ferme.
        if ferme and ferme.superficie_totale:
            autres_projets = Projet.objects.filter(ferme=ferme, statut='en_cours')
            if self.instance and self.instance.pk:
                autres_projets = autres_projets.exclude(pk=self.instance.pk)
            superficie_totale_autres = autres_projets.aggregate(total=Sum('superficie'))['total'] or 0
            if Decimal(superficie_totale_autres) + Decimal(superficie) > Decimal(ferme.superficie_totale):
                reste = Decimal(ferme.superficie_totale) - Decimal(superficie_totale_autres)
                raise forms.ValidationError(
                    f"La somme des superficies des projets en cours ne peut pas depasser celle de la ferme. "
                    f"Superficie restante disponible : {reste} ha."
                )
        return cleaned_data


class ProjetProduitForm(forms.ModelForm):
    """Form for editing product details within a project (sowing and harvest data)"""
    
    class Meta:
        model = ProjetProduit
        fields = [
            "image",
            "quantite_semences",
            "superficie_allouee",
            "date_semis",
            "date_recolte_prevue",
            "date_recolte_effective",
            "rendement_final",
            "notes",
        ]
        widgets = {
            "image": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
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
        
        projet = getattr(self.instance, 'projet', None)
        if projet and date_semis and projet.date_lancement and date_semis < projet.date_lancement:
            self.add_error('date_semis', "La date de semis ne peut pas etre anterieure au debut du projet.")
        if projet and date_semis and projet.date_fin and date_semis > projet.date_fin:
            self.add_error('date_semis', "La date de semis ne peut pas etre posterieure a la fin du projet.")
        if date_semis and date_recolte_prevue and date_recolte_prevue <= date_semis:
            self.add_error('date_recolte_prevue', "La date de recolte prevue doit etre posterieure au semis.")
        if projet and date_recolte_prevue and projet.date_fin and date_recolte_prevue > projet.date_fin:
            self.add_error('date_recolte_prevue', "La recolte prevue ne peut pas depasser la date de fin du projet.")
        
        return cleaned_data


class RendementFinalForm(forms.Form):
    """Formulaire de saisie des rendements finaux lors de la clôture du projet."""

    def __init__(self, *args, projet=None, **kwargs):
        self._projet = projet
        super().__init__(*args, **kwargs)
        if projet:
            for pp in projet.projet_produits.all():
                self.fields[f"rendement_{pp.id}"] = forms.DecimalField(
                    label=f"Rendement final - {pp.produit.nom}",
                    max_digits=10,
                    decimal_places=2,
                    required=False,
                    initial=pp.rendement_final,
                    widget=forms.NumberInput(
                        attrs={
                            "class": "form-control",
                            "placeholder": "Quantite recoltee en kg",
                            "step": "0.01",
                        }
                    ),
                )
                self.fields[f"date_recolte_{pp.id}"] = forms.DateField(
                    label=f"Date de recolte - {pp.produit.nom}",
                    required=False,
                    initial=pp.date_recolte_effective,
                    widget=forms.DateInput(
                        attrs={
                            "type": "date",
                            "class": "form-control",
                        }
                    ),
                )

    def clean(self):
        cleaned_data = super().clean()
        projet = self._projet
        if projet is not None and not projet.projet_produits.exists():
            raise forms.ValidationError(
                "Ce projet n'a aucune culture associée : ajoutez d'abord des produits "
                "depuis « Modifier le projet » avant de clôturer."
            )
        return cleaned_data

class PlantDetailsForm(forms.Form):
    """Form for inputting plant images and age in project details"""
    
    def __init__(self, *args, projet=None, **kwargs):
        super().__init__(*args, **kwargs)
        if projet:
            for pp in projet.projet_produits.all():
                self.fields[f'image_{pp.id}'] = forms.ImageField(
                    label=f"Photo - {pp.produit.nom}",
                    required=False,
                    widget=forms.ClearableFileInput(attrs={
                        'class': 'form-control',
                        'accept': 'image/*',
                        'capture': 'environment'
                    })
                )
                self.fields[f'age_plant_{pp.id}'] = forms.IntegerField(
                    label=f"Age (jours) - {pp.produit.nom}",
                    required=False,
                    min_value=0,
                    initial=pp.age_plant,
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control',
                        'placeholder': 'Age approximatif en jours'
                    })
                )


class FermeForm(forms.ModelForm):
    class Meta:
        model = Ferme
        fields = ['nom', 'description', 'pays', 'region', 'localite', 'superficie_totale', 'latitude', 'longitude']
        labels = {
            'nom': 'Nom de la ferme',
            'description': 'Description',
            'pays': 'Pays',
            'region': 'Région',
            'localite': 'Localité',
            'superficie_totale': 'Superficie totale (ha)',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
        }
        widgets = {
            'nom': forms.TextInput(
                attrs={
                    'class': 'fh-field',
                    'id': 'id_ferme_nom',
                    'placeholder': 'Ex. Ferme du Sahel',
                    'autocomplete': 'organization',
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'class': 'fh-field',
                    'id': 'id_ferme_description',
                    'rows': 4,
                    'placeholder': 'Activités, cultures principales, notes…',
                }
            ),
            'pays': forms.Select(attrs={'class': 'fh-field', 'id': 'id_ferme_pays'}),
            'region': forms.Select(attrs={'class': 'fh-field', 'id': 'id_ferme_region'}),
            'localite': forms.Select(attrs={'class': 'fh-field', 'id': 'id_ferme_localite'}),
            'superficie_totale': forms.NumberInput(
                attrs={
                    'class': 'fh-field',
                    'id': 'id_ferme_superficie',
                    'step': '0.01',
                    'min': '0',
                    'placeholder': '0',
                }
            ),
            'latitude': forms.NumberInput(
                attrs={
                    'class': 'fh-field',
                    'id': 'id_ferme_latitude',
                    'step': 'any',
                    'placeholder': 'Ex. 14.7167',
                    'inputmode': 'decimal',
                }
            ),
            'longitude': forms.NumberInput(
                attrs={
                    'class': 'fh-field',
                    'id': 'id_ferme_longitude',
                    'step': 'any',
                    'placeholder': 'Ex. -17.4677',
                    'inputmode': 'decimal',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pays'].queryset = Pays.objects.all().order_by('nom')
        self.fields['pays'].label_from_instance = lambda obj: obj.nom
        self.fields['region'].queryset = Region.objects.select_related('pays').order_by(
            'pays__nom', 'nom'
        )
        self.fields['region'].label_from_instance = lambda obj: (
            f"{obj.nom} ({obj.pays.nom})" if obj.pays_id else obj.nom
        )
        self.fields['localite'].queryset = Localite.objects.all().order_by('nom')
        self.fields['localite'].label_from_instance = lambda obj: obj.nom
        self.localites_mapping_json = json.dumps({
            str(localite.id): str(localite.pays_id or '')
            for localite in self.fields['localite'].queryset
        })


class MembreFermeForm(forms.Form):
    username = forms.CharField(
        max_length=254,
        label="Nom d'utilisateur ou email",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Nom d'utilisateur ou email de l'utilisateur inscrit"})
    )
    role = forms.ChoiceField(
        choices=[('manager', 'Manager'), ('technicien', 'Technicien'), ('ouvrier', 'Ouvrier')],
        label="Rôle",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    peut_gerer_membres = forms.BooleanField(
        required=False,
        label="Autoriser à ajouter des membres",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, ferme=None, can_delegate_members=False, **kwargs):
        self.ferme = ferme
        self.can_delegate_members = can_delegate_members
        super().__init__(*args, **kwargs)
        if not self.can_delegate_members:
            self.fields.pop('peut_gerer_membres')

    def clean_username(self):
        from django.contrib.auth.models import User
        identifiant = self.cleaned_data['username'].strip()
        if not identifiant:
            raise forms.ValidationError("Le nom d'utilisateur ou l'email est obligatoire.")

        if '@' in identifiant:
            matches = list(User.objects.filter(email__iexact=identifiant)[:2])
            if not matches:
                raise forms.ValidationError("Aucun utilisateur inscrit ne correspond à cet email.")
            if len(matches) > 1:
                raise forms.ValidationError("Plusieurs utilisateurs partagent cet email. Utilisez le nom d'utilisateur.")
            user = matches[0]
        else:
            try:
                user = User.objects.get(username=identifiant)
            except User.DoesNotExist:
                raise forms.ValidationError("Cet utilisateur n'est pas inscrit. Veuillez vérifier le nom d'utilisateur.")

        if not hasattr(user, 'profile'):
            raise forms.ValidationError("Cet utilisateur n'a pas de profil agricole.")

        if self.ferme:
            if self.ferme.proprietaire.user == user:
                raise forms.ValidationError("Cet utilisateur est déjà le propriétaire de la ferme.")
            if self.ferme.membres.filter(utilisateur=user.profile).exists():
                raise forms.ValidationError("Cet utilisateur est déjà membre de la ferme.")

        return user.profile


class DemandeAccesFermeForm(forms.Form):
    code = forms.CharField(
        max_length=12,
        label="Code de la ferme",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Saisissez le code transmis par la ferme"})
    )

    def __init__(self, *args, user_profile=None, **kwargs):
        self.user_profile = user_profile
        super().__init__(*args, **kwargs)

    def clean_code(self):
        code = self.cleaned_data['code'].strip()
        try:
            ferme = Ferme.objects.get(code_acces__iexact=code)
        except Ferme.DoesNotExist:
            raise forms.ValidationError("Aucune ferme ne correspond à ce code.")

        if self.user_profile:
            if ferme.proprietaire == self.user_profile:
                raise forms.ValidationError("Vous êtes déjà propriétaire de cette ferme.")
            if ferme.membres.filter(utilisateur=self.user_profile).exists():
                raise forms.ValidationError("Vous êtes déjà membre de cette ferme.")
            if DemandeAccesFerme.objects.filter(ferme=ferme, utilisateur=self.user_profile, statut='en_attente').exists():
                raise forms.ValidationError("Une demande est déjà en attente pour cette ferme.")

        return ferme


class TacheForm(forms.ModelForm):
    """Création / modification d'une tâche, avec restriction hiérarchique des assignations.

    Le formulaire est instancié avec :
        TacheForm(..., ferme=<Ferme>, auteur=<Profile>)
    et limite dynamiquement le queryset `assigne_a` aux membres assignables
    selon le rôle de l'auteur dans la ferme.
    """

    class Meta:
        model = Tache
        fields = ['titre', 'description', 'projet', 'assigne_a', 'priorite', 'date_echeance']
        widgets = {
            'titre': forms.TextInput(
                attrs={
                    'class': 'fh-field',
                    'placeholder': 'Ex. Préparer la parcelle nord',
                    'autocomplete': 'off',
                    'maxlength': '200',
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'class': 'fh-field',
                    'rows': 4,
                    'placeholder': 'Consignes, lieu, matériel, précisions…',
                }
            ),
            'projet': forms.Select(attrs={'class': 'fh-field'}),
            'assigne_a': forms.Select(attrs={'class': 'fh-field'}),
            'priorite': forms.Select(attrs={'class': 'fh-field'}),
            'date_echeance': forms.DateInput(attrs={'class': 'fh-field', 'type': 'date'}),
        }
        labels = {
            'titre': 'Titre',
            'description': 'Description',
            'projet': 'Projet lié',
            'assigne_a': 'Assigner à',
            'priorite': 'Priorité',
            'date_echeance': "Échéance",
        }
        help_texts = {
            'description': 'Optionnel mais recommandé pour les équipes terrain.',
            'projet': 'Limite les projets à ceux de la ferme sélectionnée.',
            'assigne_a': 'Seuls les rôles autorisés par votre niveau hiérarchique sont listés.',
            'date_echeance': 'Facultatif — doit être aujourd’hui ou une date future.',
        }

    def __init__(self, *args, ferme=None, auteur=None, **kwargs):
        self.ferme = ferme
        self.auteur = auteur
        super().__init__(*args, **kwargs)

        # Limiter les projets aux projets de la ferme
        if ferme is not None:
            self.fields['projet'].queryset = Projet.objects.filter(ferme=ferme).order_by('nom')
        self.fields['projet'].required = False
        self.fields['projet'].empty_label = '— Tâche générale (sans projet) —'

        # Limiter les assignés possibles selon la hiérarchie
        if ferme is not None and auteur is not None:
            role_auteur = role_dans_ferme(auteur, ferme)
            roles_cibles = roles_assignables_par(role_auteur)
            membres_list = list(
                MembreFerme.objects.filter(ferme=ferme, role__in=roles_cibles).select_related(
                    'utilisateur__user'
                )
            )
            profile_ids = [m.utilisateur_id for m in membres_list]
            role_labels = {m.utilisateur_id: m.get_role_display() for m in membres_list}
            self.fields['assigne_a'].queryset = (
                Profile.objects.filter(id__in=profile_ids)
                .select_related('user')
                .order_by('user__username')
            )

            def _label_assigne(profile_obj):
                nom = profile_obj.user.get_full_name() or profile_obj.user.username
                role_txt = role_labels.get(profile_obj.id, '')
                return f"{nom} ({role_txt})" if role_txt else nom

            self.fields['assigne_a'].label_from_instance = _label_assigne

    def clean(self):
        cleaned = super().clean()
        projet = cleaned.get('projet')
        assigne_a = cleaned.get('assigne_a')

        if projet and self.ferme and projet.ferme_id != self.ferme.id:
            raise forms.ValidationError("Le projet sélectionné n'appartient pas à cette ferme.")

        if assigne_a and self.ferme and self.auteur:
            role_auteur = role_dans_ferme(self.auteur, self.ferme)
            roles_autorises = roles_assignables_par(role_auteur)
            if not roles_autorises:
                raise forms.ValidationError(
                    "Votre rôle ne vous permet pas de créer des tâches dans cette ferme."
                )
            membre_cible = self.ferme.membres.filter(utilisateur=assigne_a).first()
            if membre_cible is None or membre_cible.role not in roles_autorises:
                raise forms.ValidationError(
                    "Vous ne pouvez pas assigner une tâche à ce membre (hiérarchie non respectée)."
                )

        echeance = cleaned.get('date_echeance')
        if echeance:
            from django.utils.timezone import now as _now
            if echeance < _now().date():
                self.add_error('date_echeance', "L'échéance ne peut pas être dans le passé.")

        return cleaned


class TacheStatutForm(forms.Form):
    """Mise à jour du statut d'une tâche par son assigné (ou un supérieur)."""
    statut = forms.ChoiceField(
        choices=Tache.STATUT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Nouveau statut',
    )
    commentaire_retour = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                     'placeholder': 'Commentaire (optionnel)'}),
        label='Commentaire',
    )
