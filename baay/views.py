from django.shortcuts import render

import streamlit as st

# Liste statique des fruits et légumes cultivés au Sénégal
fruits_et_legumes_senegal = [
    "Manguier (Mangue)", "Papaye", "Banane", "Orange", "Citrons et Agrumes", "Goyave", 
    "Pomme de terre douce (patate douce)", "Oignon", "Tomate", "Carotte", "Chou", "Aubergine", 
    "Poivron", "Concombre", "Haricot", "Piment", "Moringa", "Baobab", "Citrouille", "Gombo", "Tamarin"
]

# Liste dynamique pour stocker les nouveaux fruits et légumes ajoutés
fruits_et_legumes_ajoutes = []

# Fonction pour afficher les fruits et légumes avec suggestions dynamiques
def afficher_fruits_et_legumes():
    st.title("Liste des fruits et légumes cultivés au Sénégal")

    # Champ de texte pour rechercher par lettre
    st.write("Si ce que vous cherchez n'est pas dans la liste, veuillez l'écrire ci-dessous.")
    search_term = st.text_input("Rechercher un fruit ou légume (ex : carotte, tomate)")

    # Fusionner la liste statique et la liste dynamique
    all_items = fruits_et_legumes_senegal + fruits_et_legumes_ajoutes

    # Filtrer les fruits et légumes qui contiennent le terme de recherche
    if search_term:
        filtered_items = [item for item in all_items if search_term.lower() in item.lower()]
    else:
        filtered_items = all_items  # Récupérer toutes les suggestions si aucune recherche n'est effectuée

    # Afficher les suggestions sous forme de selectbox
    if filtered_items:
        selected_item = st.selectbox("Choisir un fruit ou légume", filtered_items)
        
        # Afficher un message avec l'élément sélectionné
        st.write(f"Vous avez sélectionné : {selected_item}")
    else:
        st.write("Aucun fruit ou légume trouvé.")

    # Formulaire pour ajouter un nouveau fruit ou légume
    st.write("Ajouter un nouveau fruit ou légume")
    new_item = st.text_input("Nom du nouveau fruit ou légume")
    if st.button("Ajouter"):
        if new_item:
            fruits_et_legumes_ajoutes.append(new_item)
            st.write(f"'{new_item}' a été ajouté à la liste.")
        else:
            st.write("Veuillez entrer un nom valide pour le fruit ou légume.")

# Fonction principale pour choisir l'option
def main():
    menu = ["Ajouter un fruit ou légume", "Voir les fruits et légumes"]
    choix = st.sidebar.selectbox("Choisir une option", menu)

    if choix == "Ajouter un fruit ou légume":
        st.write("Fonction pour ajouter un fruit ou légume.")
        afficher_fruits_et_legumes()
    elif choix == "Voir les fruits et légumes":
        afficher_fruits_et_legumes()

if __name__ == "__main__":
    main()

