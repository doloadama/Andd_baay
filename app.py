import streamlit as st
import requests
import re

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
    st.rerun()  # Utilisation de st.rerun() pour recharger la page

# Fonction de la page de connexion
def login_page():
    st.subheader("Page de connexion")
    login_email = st.text_input("Email (Connexion)", placeholder="Entrez votre email", key='login_email')
    login_mdp = st.text_input("Mot de passe (Connexion)", type="password", placeholder="Entrez votre mot de passe", key='login_mdp')
    if st.button("Se connecter", key='login_button'):
        st.write("Fonctionnalité de connexion non implémentée.")
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

# Fonction de la page de récupération du mot de passe
def forgot_password_page():
    st.subheader("Mot de passe oublié")
    email = st.text_input("Email", placeholder="Entrez votre email", key='forgot_email')
    if st.button("Envoyer une demande de réinitialisation", key='send_reset'):
        if not email or not email_valide(email):
            st.error("Veuillez entrer une adresse email valide.")
        else:
            # Simuler l'envoi de l'email de réinitialisation
            st.success("Une demande de réinitialisation a été envoyée à votre adresse email.")
            go_to_page('login')

    if st.button("Retour", key='back_to_login_from_forgot'):
        go_to_page('login')

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
    forgot_password_page(navigate)
