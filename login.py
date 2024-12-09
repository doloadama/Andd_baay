import streamlit as st


def login_page(navigate):
    st.title("Connexion")

    # Champs de connexion
    login_email = st.text_input("Email")
    login_mdp = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        # Logique de connexion à implémenter
        st.write("Fonction de connexion réussie - à implémenter.")

    # Lien pour réinitialiser le mot de passe
    if st.button("Mot de passe oublié?", key='reset_password'):
        navigate('reset_password')

    # Lien vers la page d'inscription
    if st.button("S'inscrire", key='to_signup'):
        navigate('signup')
