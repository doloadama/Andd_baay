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
        st.write(f"Nom: {utilisateur['nom']}, Email: {utilisateur['email']}, Date de création: {utilisateur['date_creation']}, Type utilisateur: {utilisateur['type_utilisateur']}")
else:
    st.error("Erreur lors de la récupération des utilisateurs")

# Ajouter un utilisateur
st.subheader("Ajouter un utilisateur")
nom = st.text_input("Nom")
email = st.text_input("Email")
Date_de_creation = st.text_input("Date de création")
Type_utilisateur= st.text_input("Type utilisateur")

if st.button("Créer un utilisateur"):
    data = {'nom': nom, 'email': email, 'type_utilisateur': Type_utilisateur}
    response = requests.post(API_URL, json=data)
    if response.status_code == 201:
        st.success("Utilisateur ajouté avec succès")
    else:
        st.error("Erreur lors de l'ajout de l'utilisateur")
