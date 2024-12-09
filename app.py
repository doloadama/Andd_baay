import streamlit as st
from login import login_page
from signup import signup_page
from reset_password import reset_password_page


st.title("Bienvenue sur Andd_baay : Votre Guide vers des Investissements Agricoles Réussis")
st.write("Pour commencer, inscrivez-vous si vous n'avez pas encore de compte. Si vous avez déjà un compte, connectez-vous pour accéder à votre espace personnel.")
# Initialiser l'état de session pour la page
if 'page' not in st.session_state:
    st.session_state['page'] = 'login'


def go_to_page(page_name):
    """Fonction pour changer de page."""
    st.session_state['page'] = page_name


# Logic pour changer de page
if st.session_state['page'] == 'login':
    login_page(go_to_page)
elif st.session_state['page'] == 'signup':
    signup_page(go_to_page)
elif st.session_state['page'] == 'reset_password':
    reset_password_page(go_to_page)
