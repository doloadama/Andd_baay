import django
from django.conf import settings

settings.configure(
    INSTALLED_APPS=['django.contrib.staticfiles'],
    TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates']
    }],
    STATIC_URL='/static/',
    USE_TZ=True
)

django.setup()
from django.template.loader import get_template

try:
    t = get_template('base.html')
    print('base.html OK')
except Exception as e:
    print('base.html ERROR:', e)

try:
    t = get_template('messagerie/conversation.html')
    print('conversation.html OK')
except Exception as e:
    print('conversation.html ERROR:', e)

try:
    t = get_template('messagerie/inbox.html')
    print('inbox.html OK')
except Exception as e:
    print('inbox.html ERROR:', e)
