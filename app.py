import streamlit as st
import requests
import re

API_URL = "http://127.0.0.1:8000/api/utilisateurs/"


# Fonction pour valider les emails
def email_valide(email):
    """Vérifie si l'email a un format valide."""
    regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(regex, email)


# Initialiser l'état de session pour la page
if 'page' not in st.session_state:
    st.session_state['page'] = 'login'

# Page de connexion
if st.session_state['page'] == 'login':
    st.title("Connexion")

    # Champs de connexion
    login_email = st.text_input("Email")
    login_mdp = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        # Logique de connexion à implémenter
        # Si la connexion est réussie, faites ce qui suit:
        st.write("Fonction de connexion réussie - à implémenter.")

    # Lien vers la page d'inscription
    st.markdown("[Créer un compte](#)", unsafe_allow_html=True)
    # Change l'état de la page lorsqu'on clique sur le lien
    if st.button("Inscription", key='to_signup'):
        st.session_state['page'] = 'signup'

# Page d'inscription
if st.session_state['page'] == 'signup':
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
                    st.success("Compte créé avec succès.")
                    st.session_state['page'] = 'login'
                else:
                    st.error(f"Erreur lors de la création du compte : {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Erreur de connexion à l'API : {e}")

    # Lien vers la page de connexion
    st.markdown("[Vous avez déjà un compte? Connexion](#)", unsafe_allow_html=True)
    if st.button("Se connecter", key='back_to_login'):
        st.session_state['page'] = 'login'
