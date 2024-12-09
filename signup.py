import streamlit as st
import requests
import re

API_URL = "http://127.0.0.1:8000/api/utilisateurs/"
EMAIL_VERIFICATION_URL = "http://127.0.0.1:8000/api/verify-email/"


def email_valide(email):
    """Vérifie si l'email a un format valide."""
    regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(regex, email)


def signup_page(navigate):
    st.title("Inscription")

    # Champs d'inscription
    nom = st.text_input("Nom", key='nom')
    prenom = st.text_input("Prenom", key='prenom')
    email = st.text_input("Email", key='email')
    mot_de_passe = st.text_input("Mot de passe", type="password", key='mot_de_passe')

    if st.button("Créer un compte"):
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
                    st.success("Inscription réussie! Vérifiez votre email pour activer votre compte.")
                else:
                    st.error(f"Erreur lors de l'inscription : {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Erreur de connexion à l'API : {e}")

    # Lien pour retourner à la page de connexion
    if st.button("Se connecter", key='back_to_login'):
        navigate('login')
