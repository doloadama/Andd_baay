from django.contrib.auth.hashers import make_password
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Utilisateur
from .serializers import UtilisateurSerializer
from django.http import JsonResponse


class UtilisateurListCreateAPIView(APIView):
    def get(self, request):
        utilisateurs = Utilisateur.objects.all()
        serializer = UtilisateurSerializer(utilisateurs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UtilisateurSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Cette classe définit une API RESTful pour gérer un utilisateur spécifique par son identifiant primaire (pk).
class UtilisateurDetailAPIView(APIView):

    # Méthode HTTP PUT pour mettre à jour les détails d'un utilisateur
    class UtilisateurDetailAPIView(APIView):

        def put(self, request, pk):
            utilisateur = Utilisateur.objects.get(pk=pk)

            # Supposez que new_password est un champ fourni dans request.data
            new_password = request.data.get('new_password')

            # Si un nouveau mot de passe est fourni, changez-le
            if new_password:
                utilisateur.set_password(new_password)
                utilisateur.save()

            # Actualiser les autres champs avec le sérialiseur
            serializer = UtilisateurSerializer(utilisateur, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Méthode HTTP DELETE pour supprimer un utilisateur existant
    def delete(self, request, pk):
        # Obtenez l'objet Utilisateur basé sur l'identifiant primaire (pk)
        utilisateur = Utilisateur.objects.get(pk=pk)
        # Supprimez l'utilisateur de la base de données
        utilisateur.delete()
        # Retournez une réponse avec un statut HTTP 204 qui signifie "pas de contenu"
        return Response(status=status.HTTP_204_NO_CONTENT)


@csrf_exempt
def reset_password_view(request):
    if request.method == 'POST':
        # Extraire les données du corps de la requête
        email = request.POST.get('email')
        new_password = request.POST.get('new_password')

        if not email or not new_password:
            return JsonResponse({'error': 'Email and new password are both required.'}, status=400)

        try:
            # Chercher l'utilisateur par email
            user = Utilisateur.objects.get(email=email)
            # Mettre à jour le mot de passe
            user.password = make_password(new_password)
            user.save()
            return JsonResponse({'message': 'Mot de passe réinitialisé avec succès'}, status=200)
        except Utilisateur.DoesNotExist:
            return JsonResponse({'error': 'Utilisateur introuvable.'}, status=404)
    else:
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


class ConnexionView(APIView):
    # 1. Définition d'une classe ConnexionView qui est une sous-classe de l'APIView de Django Rest Framework.
    def post(self, request):
        # 2. Redéfinition de la méthode post pour prendre en charge les requêtes POST HTTP.
        # 'request' englobe toutes les informations de la demande HTTP entrante.
        nom = request.data.get("nom")
        mot_de_passe = request.data.get("mot_de_passe")
        # 3. Récupération du nom et du mot de passe de l'utilisateur à partir du corps de la demande POST.
        utilisateur = Utilisateur.objects.get(nom=nom, password=mot_de_passe)
        # 4. Tentative d'authentification de l'utilisateur à l'aide des informations d'identification fournies.
        # La méthode 'authenticate' est une méthode de Django pour vérifier les informations d'identification d'un utilisateur.
        if utilisateur is not None:
            # 5. Si l'utilisateur est authentifié correctement (c'est-à-dire, l'objet 'utilisateur' n'est pas 'None'),
            # nous créons ou récupérons un token existant pour cet utilisateur.
            token, _ = Token.objects.get_or_create(user=utilisateur)
            # 6. Envoi du token en réponse à la requête.
            return Response({"token": token.key})
        else:
            # 7. Si l'utilisateur n'existe pas (c'est-à-dire, 'authenticate' a renvoyé 'None'), nous envoyons une réponse
            # indiquant que la tentative d'authentification a échoué.
            return Response(
                {"erreur": "L'authentification a échoué"},
                status=status.HTTP_400_BAD_REQUEST,
            )





"""
# Create your views here.
import streamlit as st
#from baay.models import FruitLegume
# Importer le modèle Django

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
    st.write(f"Si ce que vous cherchez n'est pas dans la liste veuillez l'écrire")
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
"""