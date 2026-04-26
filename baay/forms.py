from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
import json
from baay.models import Projet, ProduitAgricole, Investissement, Localite, Profile, ProjetProduit, Pays, Ferme, MembreFerme, DemandeAccesFerme, Tache


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
        fields = ['nom', 'ferme', 'image_fond', 'pays', 'localite', 'superficie', 'date_lancement', 'rendement_estime', 'statut', 'type_irrigation', 'type_engrais']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'ferme': forms.Select(attrs={'class': 'form-control'}),
            'image_fond': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'pays': forms.Select(attrs={'class': 'form-control'}),
            'localite': forms.Select(attrs={'class': 'form-control'}),
            'superficie': forms.NumberInput(attrs={'class': 'form-control'}),
            'date_lancement': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'rendement_estime': forms.NumberInput(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'type_irrigation': forms.Select(attrs={'class': 'form-control'}),
            'type_engrais': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        from_ferme = kwargs.pop('from_ferme', None)
        super().__init__(*args, **kwargs)
        # La superficie globale peut etre calculee automatiquement a partir des
        # superficies par produit (mode "per-product"). On la rend optionnelle
        # ici et la validation finale se fait dans clean().
        if 'superficie' in self.fields:
            self.fields['superficie'].required = False
        # Afficher les noms des pays et localites dans le formulaire
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
        
        # Pre-select products if editing existing project
        if self.instance and self.instance.pk:
            self.fields['produits_selection'].initial = self.instance.projet_produits.values_list('produit_id', flat=True)

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
                        'accept': 'image/*'
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
        fields = ['nom', 'description', 'pays', 'localite', 'superficie_totale']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'pays': forms.Select(attrs={'class': 'form-control'}),
            'localite': forms.Select(attrs={'class': 'form-control'}),
            'superficie_totale': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pays'].queryset = Pays.objects.all().order_by('nom')
        self.fields['pays'].label_from_instance = lambda obj: obj.nom
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
            'titre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex. Préparer la parcelle nord'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Détails, consignes, matériel...'}),
            'projet': forms.Select(attrs={'class': 'form-control'}),
            'assigne_a': forms.Select(attrs={'class': 'form-control'}),
            'priorite': forms.Select(attrs={'class': 'form-control'}),
            'date_echeance': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'titre': 'Titre',
            'description': 'Description',
            'projet': 'Projet concerné (optionnel)',
            'assigne_a': 'Assigné à',
            'priorite': 'Priorité',
            'date_echeance': "Date d'échéance",
        }

    def __init__(self, *args, ferme=None, auteur=None, **kwargs):
        self.ferme = ferme
        self.auteur = auteur
        super().__init__(*args, **kwargs)

        # Limiter les projets aux projets de la ferme
        if ferme is not None:
            self.fields['projet'].queryset = Projet.objects.filter(ferme=ferme).order_by('nom')
        self.fields['projet'].required = False
        self.fields['projet'].empty_label = '— Aucun (tâche générale) —'

        # Limiter les assignés possibles selon la hiérarchie
        if ferme is not None and auteur is not None:
            role_auteur = Tache.role_dans_ferme(auteur, ferme)
            roles_cibles = Tache.roles_assignables_par(role_auteur)
            membres_qs = MembreFerme.objects.filter(
                ferme=ferme, role__in=roles_cibles
            ).select_related('utilisateur__user')
            profile_ids = list(membres_qs.values_list('utilisateur_id', flat=True))
            self.fields['assigne_a'].queryset = (
                Profile.objects.filter(id__in=profile_ids)
                .select_related('user')
                .order_by('user__username')
            )
            self.fields['assigne_a'].label_from_instance = lambda p: (
                f"{p.user.get_full_name() or p.user.username} "
                f"({next((m.get_role_display() for m in membres_qs if m.utilisateur_id == p.id), '')})"
            )

    def clean(self):
        cleaned = super().clean()
        projet = cleaned.get('projet')
        assigne_a = cleaned.get('assigne_a')

        if projet and self.ferme and projet.ferme_id != self.ferme.id:
            raise forms.ValidationError("Le projet sélectionné n'appartient pas à cette ferme.")

        if assigne_a and self.ferme and self.auteur:
            role_auteur = Tache.role_dans_ferme(self.auteur, self.ferme)
            roles_autorises = Tache.roles_assignables_par(role_auteur)
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
