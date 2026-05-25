# ── Procfile — Types de processus pour Railway ───────────────────────────────
# Sur Railway chaque ligne correspond à un service séparé.
# Créez 3 services depuis le même dépôt GitHub, chacun avec la commande ci-dessous.
#
# SERVICE WEB  → start command: web
# SERVICE WORKER → start command: worker
# SERVICE BEAT   → start command: beat
#
# Railway détecte ce fichier automatiquement. Chaque service choisit
# sa commande dans Settings → Deploy → Custom Start Command.

web: daphne -b 0.0.0.0 -p $PORT Andd_Baayi.asgi:application
worker: celery -A Andd_Baayi worker --loglevel=info --concurrency=2 -Q celery,default
beat: celery -A Andd_Baayi beat --scheduler django_celery_beat.schedulers:DatabaseScheduler --loglevel=info
