import streamlit as st
import requests


# Fonction pour afficher la page de connexion
def login_page():
    st.markdown(
        """
        <style>
        .stButton button {
            background-color: #3897f0;
            color: white;
            border-radius: 5px;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
        }
        .stTextInput input {
            border-radius: 5px;
            border: 1px solid #ddd;
            padding: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.header("Connexion")
    username = st.text_input("Nom d'utilisateur", key="login_username")
    password = st.text_input("Mot de passe", type="password", key="login_password")

    # Bouton de connexion
    if st.button("Se connecter", key="login_button"):
        # Appeler l'API Django pour la connexion
        response = requests.post(
            "http://127.0.0.1:8000/accounts/login/",
            data={"username": username, "password": password},
        )
        if response.status_code == 200:
            st.success("Connexion réussie !")
            st.session_state.logged_in = True  # Mettre à jour l'état de la session
            st.session_state.page = (
                "home"  # Rediriger vers la page d'accueil après la connexion
            )
            st.rerun()  # Forcer le réexécution du script pour appliquer la redirection
        else:
            st.error("Identifiants invalides.")

    # Bouton pour s'inscrire
    if st.button("Pas de compte ? S'inscrire", key="signup_redirect_button"):
        st.session_state.page = "signup"
        st.rerun()  # Forcer le réexécution du script pour appliquer la redirection


# Fonction pour afficher la page d'inscription
def signup_page():
    st.markdown(
        """
        <style>
        .stButton button {
            background-color: #3897f0;
            color: white;
            border-radius: 5px;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
        }
        .stTextInput input {
            border-radius: 5px;
            border: 1px solid #ddd;
            padding: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.header("Inscription")
    username = st.text_input("Nom d'utilisateur", key="signup_username")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Mot de passe", type="password", key="signup_password")

    # Bouton d'inscription
    if st.button("S'inscrire", key="signup_button"):
        # Appeler l'API Django pour l'inscription
        response = requests.post(
            "http://127.0.0.1:8000/accounts/signup/",
            data={"username": username, "email": email, "password": password},
        )
        if response.status_code == 201:
            st.success("Inscription réussie ! Veuillez vous connecter.")
            st.session_state.page = (
                "login"  # Rediriger vers la page de connexion après l'inscription
            )
            st.rerun()  # Forcer le réexécution du script pour appliquer la redirection
        else:
            st.error("Échec de l'inscription. Veuillez réessayer.")

    # Bouton pour revenir à la page de connexion
    if st.button("Déjà un compte ? Se connecter", key="login_redirect_button"):
        st.session_state.page = "login"
        st.rerun()  # Forcer le réexécution du script pour appliquer la redirection


# Fonction pour afficher la page d'accueil
def home_page():
    st.markdown(
        """
        <style>
        .stButton button {
            background-color: #3897f0;
            color: white;
            border-radius: 5px;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.header("Bienvenue sur l'application !")
    st.write("Vous êtes connecté avec succès.")

    # Bouton pour se déconnecter
    if st.button("Se déconnecter", key="logout_button"):
        st.session_state.logged_in = False
        st.session_state.page = (
            "login"  # Rediriger vers la page de connexion après la déconnexion
        )
        st.rerun()  # Forcer le réexécution du script pour appliquer la redirection


# Fonction principale
def main():
    st.set_page_config(page_title="Authentification", page_icon="🔐")

    # Initialiser l'état de la session
    if "page" not in st.session_state:
        st.session_state.page = "login"  # Afficher la page de connexion par défaut
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    # Afficher la page appropriée
    if st.session_state.page == "login":
        login_page()
    elif st.session_state.page == "signup":
        signup_page()
    elif st.session_state.page == "home":
        home_page()


# Lancer l'application
if __name__ == "__main__":
    main()
