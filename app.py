import time
import streamlit as st
import requests
import re

# Remplace par l'URL de ton API
API_URL = "http://127.0.0.1:8000/api/utilisateurs/"

# Fonction pour valider les emails
def email_valide(email):
    """Vérifie si l'email a un format valide."""
    regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(regex, email)

# Fonction pour changer de page
def go_to_page(page_name):
    """Fonction pour changer de page."""
    st.session_state.page = page_name
    st.rerun()

# Fonction de la page de connexion
def login_page():
    nom = st.text_input("Nom d'utilisateur")
    mot_de_passe = st.text_input("Mot de passe", type='password')

    if st.button('Connexion'):
        response = requests.post('http://localhost:8000/api/v1/connexion',
                                 data={'nom': nom, 'mot_de_passe': mot_de_passe})
        if response.status_code == 200:
            token = response.json().get('token')
            st.success('Connexion réussie! Votre token : ' + token)
            go_to_page('main')
        else:
            st.error('Erreur de connexion.')

    if st.button("S'inscrire", key='to_signup'):
        go_to_page('signup')
    
    if st.button("Mot de passe oublié?", key='forgot_password'):
        go_to_page('forgot_password')

    if st.button("Retour", key='back_to_home'):
        go_to_page('home')  # Redirige vers la première page

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
                    data={"email": email, "new_password": new_password},
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

def main():
    nav = ["Profil","Projet","Localités","Tendances marché"]
    st.navigation(nav)

    return go_to_page('main')



# Initialiser l'état de session pour la page
if 'page' not in st.session_state:
    st.session_state.page = 'home'

# Page d'accueil
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
#elif st.session_state.page == 'forgot_password':
    #forgot_password_page()
elif st.session_state.page == 'main':
    st.title("Votre espace personnel")
    st.subheader("Votre profil")
    st.write("Ceci est votre profil personnel. Vous pouvez modifier les informations que vous souhaitez.")
    st.write("Vous pouvez aussi modifier votre mot de passe, ou supprimer votre compte.")
    if st.button("Modifier le profil", key='main_to_edit_profile'):
        st.subheader("Reinitialisation du mot de passe")
        reset_password_page(st.text_input("Email", key="reset_password_email"))
