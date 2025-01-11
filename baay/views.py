from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from baay.models import Profile


@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')

    if not username or not email or not password:
        return Response({"error": "Please provide all fields"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, email=email, password=password, last_name=last_name, first_name=first_name)
    return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)
    if user:
        login(request, user)
        return Response({"message": "Login successful"}, status=status.HTTP_200_OK)
    else:
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


"""@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    email = request.data.get('email')
    user = User.objects.filter(email=email).first()

    if user:
        # Generate a random token
        token = get_random_string(length=32)

        # Ensure the user has a profile
        profile, created = Profile.objects.get_or_create(user=user)

        # Save the token to the user's profile
        profile.reset_token = token
        profile.save()

        # Create the reset link
        reset_link = f"http://127.0.0.1:8000/accounts/reset-password/{token}/"

        # Send the email
        send_mail(
            "Password Reset Request",
            f"Click the link to reset your password: {reset_link}",
            "noreply@example.com",
            [email],
            fail_silently=False,
        )
        return Response({"message": "Password reset email sent"}, status=status.HTTP_200_OK)
    else:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
"""

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    email = request.data.get('email')
    new_password = request.data.get('new_password')

    # Vérifier si l'utilisateur existe
    user = User.objects.filter(email=email).first()
    if not user:
        return Response({"error": "Aucun utilisateur trouvé avec cette adresse e-mail."}, status=status.HTTP_404_NOT_FOUND)


    # Réinitialiser le mot de passe
    user.set_password(new_password)
    user.save()

    # Effacer le token de réinitialisation
    user.profile.reset_token = None
    user.profile.save()

    return Response({"message": "Mot de passe réinitialisé avec succès."}, status=status.HTTP_200_OK)