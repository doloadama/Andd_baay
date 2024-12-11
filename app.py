import streamlit as st
import requests
import re

# Remplace par l'URL de ton API
API_URL = "http://127.0.0.1:8000/api/utilisateurs/"
API_LOGIN_URL = "http://127.0.0.1:8000/api/utilisateurs/login_view/"
# Fonction pour valider les emails
def email_valide(email):
    """Vérifie si l'email a un format valide."""
    if not email or not isinstance(email, str):
        return False
    regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(regex, email)

# Fonction pour changer de page
def go_to_page(page_name):
    """Fonction pour changer de page."""
    st.session_state.page = page_name
    st.rerun()


def login_page():
    """
    Affiche la page de connexion et gère l'authentification de l'utilisateur.
    """
    st.title("Page de Connexion")

    # Champs pour le nom d'utilisateur et le mot de passe
    nom = st.text_input("Nom d'utilisateur", key="nom_utilisateur")
    mot_de_passe = st.text_input("Mot de passe", type='password', key="mot_de_passe")

    # Bouton pour la connexion
    if st.button('Connexion'):
        # Validation des champs
        if not nom or not mot_de_passe:
            st.warning("Veuillez remplir tous les champs.")
            return

        try:
            # Envoi de la requête POST à l'API
            response = requests.post(
                API_LOGIN_URL,
                data={"nom": nom, "mot_de_passe": mot_de_passe}
            )

            # Traitement de la réponse
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    st.success("Connexion réussie !")
                    st.write(data)  # Affiche les données renvoyées par l'API
                    go_to_page('main')  # Redirige vers la page principale
                else:
                    st.error("Identifiants invalides. Veuillez réessayer.")
            else:
                st.error(f"Erreur serveur : {response.status_code}")

        except requests.exceptions.RequestException as e:
            st.error(f"Erreur lors de la connexion : {e}")


    if st.button("S'inscrire", key='to_signup'):
        go_to_page('signup')

    if st.button("Mot de passe oublié?", key='forgot_password'):
        go_to_page('forgot_password')

    if st.button("Retour", key='back_to_home'):
        go_to_page('home')




# Fonction de la page d'inscription
def signup_page():
    st.subheader("Inscrivez-vous et commencez votre aventure agricole")
    nom = st.text_input("Nom", key='signup_nom')
    prenom = st.text_input("Prenom", key='signup_prenom')
    email = st.text_input("Email", key='signup_email')
    mot_de_passe = st.text_input("Mot de passe", type="password", key='signup_mot_de_passe')

    if st.button("Créer un utilisateur", key='create_user'):
        if not nom or not prenom or not email or not mot_de_passe:
            st.error("Veuillez remplir tous les champs.")
        elif not email_valide(email):
            st.error("Veuillez entrer une adresse email valide.")
        else:
            try:
                data = {
                    'prenom': prenom,
                    'nom': nom,
                    'email': email,
                    'mot_de_passe': mot_de_passe
                }
                response = requests.post(API_URL, json=data)
                if response.status_code == 201:
                    st.success("Utilisateur ajouté avec succès. Redirection vers la page de connexion...")
                    go_to_page('login')
                else:
                    st.error(f"Erreur lors de l'ajout de l'utilisateur : {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Erreur de connexion à l'API : {e}")

    if st.button("Retour", key='back_to_login'):
        go_to_page('login')

# Fonction de la page de demande de réinitialisation du mot de passe
def forgot_password_page():
    st.subheader("Réinitialisation du mot de passe")
    email = st.text_input("Veuillez insérer votre email", key='forgot_password_email')

    if st.button("Envoyer le lien de réinitialisation", key='send_reset_link'):
        if not email or not email_valide(email):
            st.error("Veuillez entrer une adresse email valide.")
        else:
            try:
                response = requests.post(f"{API_URL}send_reset_link/", data={'email': email})
                if response.status_code == 200:
                    st.success("Un email de réinitialisation de mot de passe a été envoyé.")
                    go_to_page('reset_password')
                else:
                    st.error(f"Erreur lors de l'envoi du lien de réinitialisation : {response.text}")
                    st.error(f"Statut de la réponse : {response.status_code}")
                    st.error(f"Contenu de la réponse : {response.content.decode('utf-8')}")
            except requests.exceptions.RequestException as e:
                st.error(f"Erreur de connexion à l'API : {e}")

    if st.button("Retour", key='back_to_login_from_forgot'):
        go_to_page('login')

# Fonction de la page de réinitialisation du mot de passe
def reset_password_page(email):
    st.subheader("Réinitialiser le mot de passe")

    new_password = st.text_input(
        "Nouveau mot de passe", type="password", key="new_password"
    )
    confirm_password = st.text_input(
        "Confirmer le nouveau mot de passe", type="password", key="confirm_password"
    )

    if st.button("Changer le mot de passe", key="update_password"):
        if new_password != confirm_password:
            st.error("Les mots de passe ne correspondent pas.")
        elif len(new_password) < 8:
            st.error("Le mot de passe doit contenir au moins 8 caractères.")
        else:
            try:
                API_RESET_PASSWORD_URL = (
                    "http://127.0.0.1:8000/api/utilisateurs/reset_password/"
                )
                response = requests.post(
                    API_RESET_PASSWORD_URL,
                    data={"email": email, "mot_de_passe": new_password},
                )

                if response.status_code == 200:
                    st.success(
                        "Votre mot de passe a été modifié avec succès. Veuillez vous reconnecter."
                    )
                    go_to_page("login")
                else:
                    error_message = response.json().get(
                        "error", "Une erreur inattendue s'est produite."
                    )
                    st.error(f"Erreur : {error_message}")

            except requests.exceptions.RequestException as e:
                st.error(f"Erreur de connexion à l'API : {e}")

def page_profil():
    st.write("Bienvenue sur la page Profil")


def page_projet():
    st.write("Bienvenue sur la page Projet")


def page_localites():
    st.write("Bienvenue sur la page Localités")


def page_tendances():
    st.write("Bienvenue sur la page Tendances Marché")


PAGES = {
    "Profil": page_profil,
    "Projet": page_projet,
    "Localités": page_localites,
    "Tendances marché": page_tendances,
}


def main():
    st.sidebar.title("Navigation")
    choix = st.sidebar.select_slider("Aller à", list(PAGES.keys()))
    PAGES[choix]()

# Initialiser l'état de session pour la page
if 'page' not in st.session_state:
    st.session_state.page = 'home'

def hash_password(password):
    """Hash le mot de passe pour plus de sécurité."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()
if st.session_state.page == 'home':
    st.title("Bienvenue sur Andd_baay : Votre Guide vers des Investissements Agricoles Réussis")
    st.write("Pour commencer, inscrivez-vous si vous n'avez pas encore de compte. Si vous avez déjà un compte, connectez-vous pour accéder à votre espace personnel.")
    if st.button("S'inscrire", key='home_to_signup'):
        go_to_page('signup')
    if st.button("Se connecter", key='home_to_login'):
        go_to_page('login')

# Logic pour changer de page
if st.session_state.page == 'login':
    login_page()

elif st.session_state.page == 'signup':
    signup_page()

elif st.session_state.page == 'forgot_password':
    reset_password_page(st.text_input("Email"))

elif st.session_state.page == 'main':
    st.title("Votre espace personnel")
    st.subheader("Votre profil")
    st.write("Ceci est votre profil personnel. Vous pouvez modifier les informations que vous souhaitez.")
    st.write("Vous pouvez aussi modifier votre mot de passe, ou supprimer votre compte.")
    if st.button("Modifier le profil", key='main_to_edit_profile'):
        st.subheader("Reinitialisation du mot de passe")
        reset_password_page(st.text_input("Email", key="reset_password_email"))