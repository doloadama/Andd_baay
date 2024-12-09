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
def changer_page(nouvelle_page):
    st.session_state['page'] = nouvelle_page

# Initialiser l'état de session pour la page et l'état d'affichage du formulaire d'inscription
if 'page' not in st.session_state:
    st.session_state['page'] = 'home'
if 'show_signup_form' not in st.session_state:
    st.session_state['show_signup_form'] = False

# Page d'accueil avec les boutons de redirection
if st.session_state['page'] == 'home':
    st.title("Bienvenue sur Andd_baay : Votre Guide vers des Investissements Agricoles Réussis")
    if st.button("S'inscrire"):
        st.session_state['show_signup_form'] = True  # Afficher le formulaire d'inscription
    if st.button("Se connecter"):
        changer_page('login')  # Rediriger vers la page de connexion

# Page d'inscription
if st.session_state['page'] == 'signup' or st.session_state['show_signup_form']:
    st.title("Inscription")
    st.subheader("Inscrivez-vous et commencez votre aventure agricole")

    # Champs d'entrée pour le nouvel utilisateur
    nom = st.text_input("Nom", key='nom')
    prenom = st.text_input("Prenom", key='prenom')
    email = st.text_input("Email", key='email')
    mot_de_passe = st.text_input("Mot de passe", type="password", key='mot_de_passe')

    if st.button("Créer un utilisateur"):
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
                    changer_page('login')  # Changer la page à 'login'
                else:
                    st.error(f"Erreur lors de l'ajout de l'utilisateur : {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Erreur de connexion à l'API : {e}")

    if st.button("Retour"):
        changer_page('home')  # Retour à la page d'accueil

# Page de connexion simulée
if st.session_state['page'] == 'login':
    st.subheader("Page de connexion")
    # Simuler les champs de connexion
    login_email = st.text_input("Email (Connexion)", placeholder="Entrez votre email")
    login_mdp = st.text_input("Mot de passe (Connexion)", type="password", placeholder="Entrez votre mot de passe")
    if st.button("Se connecter"):
        st.write("Fonctionnalité de connexion non implémentée.")
        # Implémentez la logique de connexion ici

    if st.button("Retour"):
        changer_page('home')  # Retour à la page d'accueil

