import streamlit as st
import requests
import re
import time

API_URL = "http://127.0.0.1:8000/api/utilisateurs/"

st.title("Gestion des Utilisateurs")

# Afficher la liste des utilisateurs
st.subheader("Liste des utilisateurs")
response = requests.get(API_URL)
if response.status_code == 200:
    utilisateurs = response.json()
    for utilisateur in utilisateurs:
        st.write(
            f" Prenom: {utilisateur['prenom']}, "
            f"Nom: {utilisateur['nom']}, "
            f"Email: {utilisateur['email']}, "
            f"Date de création: {utilisateur['date_creation']}"
        )
else:
    st.error(f"Erreur lors de la récupération des utilisateurs : Statut {response.status_code}")

# Ajouter un utilisateur
st.title("Bienvenue sur Andd_baay : Votre Guide vers des Investissements Agricoles Réussis")
st.subheader("Inscrivez-vous et commencez votre aventure agricole")

# Champs d'entrée pour le nouvel utilisateur
nom = st.text_input("Nom")
prenom = st.text_input("Prenom")
email = st.text_input("Email")
mot_de_passe = st.text_input("Mot de passe", type="password")


def email_valide(email):
    """Vérifie si l'email a un format valide."""
    regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(regex, email)


if st.button("Créer un utilisateur"):
    # Validation des champs
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
                st.success("Utilisateur ajouté avec succès")
                # Attendez une ou deux secondes pour montrer le message
                time.sleep(2)
                # Rafraichir la page
                st.experimental_rerun()
            else:
                st.error(f"Erreur lors de l'ajout de l'utilisateur : {response.text}")
        except requests.exceptions.RequestException as e:
            st.error(f"Erreur de connexion à l'API : {e}")
