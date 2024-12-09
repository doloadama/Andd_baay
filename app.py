import streamlit as st
import requests
import re
import time

# URL de l'API des utilisateurs
API_URL = "http://127.0.0.1:8000/api/utilisateurs/"

# Titre principal de l'application
st.title("Gestion des Utilisateurs")

# Sous-titre pour la liste des utilisateurs
st.subheader("Liste des utilisateurs")

# Effectuer une requête GET pour récupérer la liste des utilisateurs
response = requests.get(API_URL)
if response.status_code == 200:
    utilisateurs = response.json()
    # Parcourir et afficher chaque utilisateur
    for utilisateur in utilisateurs:
        st.write(
            f" Prenom: {utilisateur['prenom']}, "
            f"Nom: {utilisateur['nom']}, "
            f"Email: {utilisateur['email']}, "
            f"Date de création: {utilisateur['date_creation']}"
        )
else:
    # Afficher un message d'erreur en cas de problème lors de la récupération
    st.error(f"Erreur lors de la récupération des utilisateurs : Statut {response.status_code}")

# Titre et sous-titre pour l'ajout d'un utilisateur
st.title("Bienvenue sur Andd_baay : Votre Guide vers des Investissements Agricoles Réussis")
st.subheader("Inscrivez-vous et commencez votre aventure agricole")


# Créer une fonction pour réinitialiser les champs
def reset_inputs():
    st.session_state['nom'] = ''
    st.session_state['prenom'] = ''
    st.session_state['email'] = ''
    st.session_state['mot_de_passe'] = ''


# Champs d'entrée pour les informations du nouvel utilisateur, avec des clés uniques
nom = st.text_input("Nom", key='nom')
prenom = st.text_input("Prenom", key='prenom')
email = st.text_input("Email", key='email')
mot_de_passe = st.text_input("Mot de passe", type="password", key='mot_de_passe')


def email_valide(email):
    """Vérifie si l'email a un format valide."""
    # Expression régulière pour le format d'un email
    regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(regex, email)


# Bouton pour créer un utilisateur
if st.button("Créer un utilisateur"):
    # Vérifier si tous les champs sont remplis correctement
    if not nom or not prenom or not email or not mot_de_passe:
        st.error("Veuillez remplir tous les champs.")
    elif not email_valide(email):
        st.error("Veuillez entrer une adresse email valide.")
    else:
        try:
            # Préparer les données de l'utilisateur pour l'envoi à l'API
            data = {
                'prenom': prenom,
                'nom': nom,
                'email': email,
                'mot_de_passe': mot_de_passe
            }
            # Effectuer une requête POST pour ajouter l'utilisateur
            response = requests.post(API_URL, json=data)
            if response.status_code == 201:
                st.success("Utilisateur ajouté avec succès")
                # Réinitialiser les champs d'entrée après succès
                reset_inputs()
            else:
                # Afficher un message d'erreur si l'ajout échoue
                st.error(f"Erreur lors de l'ajout de l'utilisateur : {response.text}")
        except requests.exceptions.RequestException as e:
            # Gérer les exceptions de requêtes API
            st.error(f"Erreur de connexion à l'API : {e}")
