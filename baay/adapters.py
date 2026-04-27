import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User
from django.utils.text import slugify

logger = logging.getLogger(__name__)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for django-allauth that populates user fields
    (first_name, last_name, username) from Google OAuth profile data.
    """

    def pre_social_login(self, request, sociallogin):
        """Auto-connect social login to existing user if email matches."""
        if sociallogin.is_existing:
            return

        email = (sociallogin.account.extra_data.get('email')
                 or getattr(sociallogin.user, 'email', None))
        if email:
            user = User.objects.filter(email__iexact=email).order_by('-date_joined').first()
            if user:
                sociallogin.connect(request, user)
                logger.info(
                    "Connected existing user %s to new social account %s",
                    user.email, sociallogin.account.provider,
                )

    def populate_user(self, request, sociallogin, data):
        """Populate the user from Google OAuth data."""
        user = super().populate_user(request, sociallogin, data)
        extra_data = sociallogin.account.extra_data

        # Google specific fields
        given_name = extra_data.get('given_name', '')
        family_name = extra_data.get('family_name', '')
        full_name = extra_data.get('name', '')

        # Fallback logic for name extraction
        if given_name:
            user.first_name = given_name
        elif full_name:
            parts = full_name.split()
            user.first_name = parts[0] if parts else ''

        if family_name:
            user.last_name = family_name
        elif full_name and len(full_name.split()) > 1:
            user.last_name = ' '.join(full_name.split()[1:])

        # Ensure email is set
        email = extra_data.get('email') or data.get('email')
        if email:
            user.email = email.lower().strip()

        return user

    def save_user(self, request, sociallogin, form=None):
        """Save the user and ensure a valid username is generated."""
        user = super().save_user(request, sociallogin, form)

        # Generate username from email if not set or empty
        if not user.username and user.email:
            base_username = slugify(user.email.split('@')[0]) or 'user'
            base_username = base_username[:140]
            candidate = base_username
            i = 1
            while User.objects.filter(username__iexact=candidate).exists():
                suffix = str(i)
                candidate = f"{base_username[:150 - len(suffix) - 1]}.{suffix}"
                i += 1
            user.username = candidate
            user.save(update_fields=['username'])

        logger.info(
            "Social user saved: id=%s username=%s email=%s provider=%s",
            user.pk, user.username, user.email, sociallogin.account.provider,
        )
        return user

    def get_connect_redirect_url(self, request, socialaccount):
        """Redirect after connecting a social account."""
        return '/dashboard/'
