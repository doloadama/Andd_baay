"""
Management command to upload authentication background images to Cloudinary.

Usage:
    python manage.py upload_auth_images

This uploads:
    - images/image2.jpg → andd-baayi/auth/login-bg
    - images/image.jpg → andd-baayi/auth/signup-bg

After upload, add these URLs to your environment or settings:
    LOGIN_BG_CLOUDINARY_URL=<url>
    SIGNUP_BG_CLOUDINARY_URL=<url>
"""

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Upload authentication background images to Cloudinary"

    def handle(self, *args, **options):
        if not getattr(settings, "CLOUDINARY_ACTIVE", False):
            self.stdout.write(
                self.style.WARNING(
                    "Cloudinary not configured (CLOUDINARY_URL missing). "
                    "Images will use static file fallback."
                )
            )
            self.stdout.write("Static paths that will be used:")
            self.stdout.write("  - Login:  images/image2.jpg")
            self.stdout.write("  - Signup: images/image.jpg")
            return

        from baay.services import upload_static_to_cloudinary

        images_to_upload = [
            ("images/image2.jpg", "auth/login-bg", "LOGIN_BG_CLOUDINARY_URL"),
            ("images/image.jpg", "auth/signup-bg", "SIGNUP_BG_CLOUDINARY_URL"),
        ]

        self.stdout.write("Uploading images to Cloudinary...")

        for static_path, public_id, env_var in images_to_upload:
            try:
                result = upload_static_to_cloudinary(
                    static_path=static_path,
                    public_id=public_id,
                    overwrite=True,
                    invalidate=True,
                )
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Uploaded {static_path} → {result['public_id']}")
                )
                self.stdout.write(f"  URL: {result['secure_url']}")
                self.stdout.write(f"  Add to environment: {env_var}={result['secure_url']}")
            except FileNotFoundError:
                self.stdout.write(
                    self.style.ERROR(f"✗ File not found: {static_path}")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Failed to upload {static_path}: {e}")
                )

        self.stdout.write("\nDone! Add the URLs above to your .env file or settings.")
        self.stdout.write("Example .env entries:")
        self.stdout.write("  LOGIN_BG_CLOUDINARY_URL=https://res.cloudinary.com/.../login-bg.jpg")
        self.stdout.write("  SIGNUP_BG_CLOUDINARY_URL=https://res.cloudinary.com/.../signup-bg.jpg")
