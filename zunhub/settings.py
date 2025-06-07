from pathlib import Path
from dotenv import load_dotenv
import json
import os
from django.core.serializers.json import DjangoJSONEncoder


load_dotenv()  # Load environment variables from .env file

BYBIT_RECEIVE_DETAILS = json.loads(os.getenv("BYBIT_RECEIVE_DETAILS", "{}"))
BITGET_RECEIVE_DETAILS = json.loads(os.getenv("BITGET_RECEIVE_DETAILS", "{}"))
MEXC_RECEIVE_DETAILS = json.loads(os.getenv("MEXC_RECEIVE_DETAILS", "{}"))
GATEIO_RECEIVE_DETAILS = json.loads(os.getenv("GATEIO_RECEIVE_DETAILS", "{}"))

BINANCE_RECEIVE_DETAILS = json.loads(os.getenv("BINANCE_RECEIVE_DETAILS", "{}"))
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')

# Toncenter API Key
TONCENTER_API_KEY = os.getenv("TONCENTER_API_KEY")
TON_API_URL = os.getenv("TON_API_URL")

# BSC Configuration
BSC_SENDER_PRIVATE_KEY = os.getenv("BSC_SENDER_PRIVATE_KEY")
BSC_RPC_URL = os.getenv("BSC_RPC_URL")


BASE_URL = os.getenv("BASE_URL")
FLUTTERWAVE_PUBLIC_KEY = os.getenv("FLUTTERWAVE_PUBLIC_KEY")
FLUTTERWAVE_SECRET_KEY = os.getenv("FLUTTERWAVE_SECRET_KEY")
FLUTTERWAVE_HASH_KEY = os.getenv("FLUTTERWAVE_HASH_KEY")



# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'))

# VTPASS Configuration
VTPASS_API_KEY       = os.getenv("VTPASS_API_KEY", "")
VTPASS_SECRET_KEY    = os.getenv("VTPASS_SECRET_KEY", "")
VTPASS_SANDBOX_URL   = os.getenv("VTPASS_SANDBOX_URL", "")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-lr99y20wxx3m2u(36j7zu(s88618g6j!sd!_!(h9a4^+sz04u7'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

AUTH_USER_MODEL = 'accounts.User'

TON_SEQNO_CHECK_INTERVAL = 10  # Seconds between seqno checks
TON_SEQNO_MAX_ATTEMPTS = 5    # Number of attempts


# Celery settings
CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Using Redis as the broker
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'


# Optional: periodic task schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'check-sell-orders-every-minute': {
        'task': 'bills.tasks.check_sell_orders',
        'schedule': crontab(minute='*/1'),
    },
}


# Add caching config
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/1",  # Use db 1 to separate from Celery
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Cache timeout (in seconds)
CACHE_TTL = 300  # 5 minutes


# Enable logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
}





# Application definition
INSTALLED_APPS = [
    'accounts.apps.AccountsConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'widget_tweaks',
    'channels',
    'p2p',
    'bills',
    'gasfee',
    'payments',
]

# Tell Django to use ASGI instead of WSGI.
ASGI_APPLICATION = "zunhub.asgi.application"

# Configure channel layers (Redis backend):
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'zunhub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'zunhub.wsgi.application'




# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]  # Where your static files live
STATIC_ROOT = BASE_DIR / "staticfiles"    # Where static files are collected

# Media (optional)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'



# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

