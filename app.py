from Streamlit.login import *
from Streamlit.signup import *
from Streamlit.passreset import *
from utils import *


@st.fragment()
# Fonction pour afficher la page d'accueil
def home_page():
    set_background_color("#f0f8ff")  # Couleur de fond pour la page d'accueil
    st.header("Bienvenue sur l'application !")
    st.write("Vous êtes connecté avec succès.")


    if st.button("Se déconnecter", key="logout_button"):
        st.session_state.logged_in = False
        st.session_state.page = "login"
        st.rerun()

# Fonction principale
def main():
    st.set_page_config(page_title="Authentification", page_icon="🔐")

    # Initialiser l'état de la session
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = True
    if "username" not in st.session_state:
        st.session_state.username = None

    # Gérer la page de confirmation de réinitialisation du mot de passe
    if st.session_state.logged_in:
        if st.session_state.page == "password_request_page":
            password_reset_request_page()
        else:
            # Afficher la page appropriée
            if st.session_state.page == "login":
                login_page()
            elif st.session_state.page == "signup":
                signup_page()
            elif st.session_state.page == "home":
                if st.session_state.logged_in:
                    home_page()
                else:
                    st.session_state.page = "login"
                    st.rerun()
            elif st.session_state.page == "password_reset_request":
                password_reset_request_page()

# Lancer l'application
if __name__ == "__main__":
    main()