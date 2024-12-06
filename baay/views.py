from django.shortcuts import render


# Create your views here.
import streamlit as st
# Liste statique des fruits et légumes cultivés au Sénégal
fruits_et_legumes_senegal = [
    "Manguier (Mangue)", "Papaye", "Banane", "Orange", "Citrons et Agrumes", "Goyave", 
    "Pomme de terre douce (patate douce)", "Oignon", "Tomate", "Carotte", "Chou", "Aubergine", 
    "Poivron", "Concombre", "Haricot", "Piment", "Moringa", "Baobab", "Citrouille", "Gombo", "Tamarin"
]

# Fonction pour afficher les fruits et légumes avec suggestions dynamiques
def afficher_fruits_et_legumes():
    st.title("Liste des fruits et légumes cultivés au Sénégal")
    
    # Champ de texte pour rechercher par lettre
    search_term = st.text_input("Rechercher un fruit ou légume (ex : carotte, tomate)")

    # Filtrer les fruits et légumes qui contiennent le terme de recherche
    if search_term:
        filtered_items = [item for item in fruits_et_legumes_senegal if search_term.lower() in item.lower()]
    else:
        filtered_items = fruits_et_legumes_senegal  # Récupérer toutes les suggestions si aucune recherche n'est effectuée

    # Afficher les suggestions sous forme de selectbox
    if filtered_items:
        selected_item = st.selectbox("Choisir un fruit ou légume", filtered_items)
        
        # Afficher un message avec l'élément sélectionné
        st.write(f"Vous avez sélectionné : {selected_item}")
    else:
        st.write("Aucun fruit ou légume trouvé.")

# Fonction principale pour choisir l'option
def main():
    menu = ["Ajouter un fruit ou légume", "Voir les fruits et légumes"]
    choix = st.sidebar.selectbox("Choisir une option", menu)

    if choix == "Ajouter un fruit ou légume":
        # Vous pouvez ajouter une fonction pour ajouter un fruit ou légume ici
        st.write("Fonction pour ajouter un fruit ou légume.")
    elif choix == "Voir les fruits et légumes":
        afficher_fruits_et_legumes()

if __name__ == "__main__":
    main()
