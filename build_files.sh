#!/bin/bash
# Vercel build script
echo "Running collectstatic..."
python manage.py collectstatic --noinput 2>&1 || true

echo "Running migrations..."
python manage.py migrate --noinput 2>&1 || true

echo "Build complete!"
