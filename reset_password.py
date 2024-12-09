import streamlit as st


def reset_password_page(navigate):
    st.title("Réinitialiser le mot de passe")

    email = st.text_input("Entrez votre email pour réinitialiser votre mot de passe")

    if st.button("Envoyer la demande de réinitialisation"):
        # Logique pour envoyer un email de réinitialisation (via une API)
        st.write("Un email de réinitialisation a été envoyé - à implémenter.")
        # Normalement, vous vérifieriez ici si l'email existe et envoyez un lien ou un code de réinitialisation.

    # Une fois le lien reçu, redirige l'utilisateur pour entrer le nouveau mot de passe
    # Cette partie dépendrait typiquement d'un paramètre sécurisé de lien reçu par email
    if st.button("Retour à la connexion", key='back_to_login'):
        navigate('login')
