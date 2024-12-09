import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/api/utilisateurs/"

st.title("Gestion des Utilisateurs")

# Afficher la liste des utilisateurs
st.subheader("Liste des utilisateurs")
response = requests.get(API_URL)
if response.status_code == 200:
    utilisateurs = response.json()
    for utilisateur in utilisateurs:
        st.write(
            f" Prenom: {utilisateur['prenom']}, Nom: {utilisateur['nom']}, Email: {utilisateur['email']}, Date de création: {utilisateur['date_creation']}")
else:
    st.error(f"Erreur lors de la récupération des utilisateurs : Statut {response.status_code}")

# Ajouter un utilisateur
st.title("Bienvenue sur Andd_baay : Votre Guide vers des Investissements Agricoles Réussis")
st.subheader("Inscrivez-vous et commencez votre aventure agricole")
nom = st.text_input("Nom")
prenom= st.text_input("Prenom")
email = st.text_input("Email")



if st.button("Créer un utilisateur"):
    if not nom or not prenom or not email:
        st.error("Veuillez remplir tous les champs.")
    else:
        try:
            data = {'prenom': prenom, 'nom': nom, 'email': email}
            response = requests.post(API_URL, json=data)
            if response.status_code == 201:
                st.success("Utilisateur ajouté avec succès")
            else:
                st.error(f"Erreur lors de l'ajout de l'utilisateur : {response.text}")
        except requests.exceptions.RequestException as e:
            st.error(f"Erreur de connexion à l'API : {e}")
