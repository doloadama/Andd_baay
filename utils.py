"""from django.contrib.auth.hashers import make_password
from baay.models import Profile
from django.contrib.auth.hashers import check_password


def hash_existing_passwords():
    utilisateurs = Utilisateur.objects.all()  # Récupérer tous les utilisateurs
    for utilisateur in utilisateurs:
        if utilisateur.mot_de_passe and not utilisateur.mot_de_passe.startswith('pbkdf2_'):  # Vérifiez si le mot de passe est déjà haché
            utilisateur.mot_de_passe = make_password(utilisateur.mot_de_passe)  # Hacher le mot de passe
            utilisateur.save()  # Sauvegarder l'utilisateur avec le mot de passe mis à jour
            print(f"Mot de passe pour {utilisateur.nom} a été haché.")
    print("Tous les mots de passe ont été mis à jour.")


def authenticate_user(username, password):
    try:
        user = Utilisateur.objects.get(nom=username)
    except Utilisateur.DoesNotExist:
        return None

    if check_password(password, user.password):
        return user
    return None
"""