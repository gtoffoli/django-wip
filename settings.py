"""
Django settings for wip project.

Generated by 'django-admin startproject' using Django 1.9.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os, sys

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wip.settings')

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '8ex1mkis_48z89$=+08t^sd3h5zt&$@k+m*_5rn30!pqe6pbp)'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

if sys.platform.count('linux'):
    DEBUG = False
    ALLOWED_HOSTS = ["localhost", ".fairvillage.eu", ".fairvillage.it"]
else:
    DEBUG = True

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'allauth',
    'allauth.account',
    'bootstrap3',
    'menu',
    'httpproxy',
    # 'kombu.transport.django',
    'wip',
]

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'wip.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "wip", "templates")],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'wip.context_processors.context_processor',
            ],
        'loaders': [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
            ],
        },
    },
]

WSGI_APPLICATION = 'wip.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
#   'default': {
#        'ENGINE': 'django.db.backends.sqlite3',
#        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#    }
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'wip',
        'USER': 'admin',
        'PASSWORD': 'giotto',
        'HOST': 'localhost',
        'PORT': '',
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'

# TIME_ZONE = 'UTC'
TIME_ZONE = 'Europe/Rome'

USE_I18N = True

USE_L10N = True

USE_TZ = True

SITE_ID = 1
SITE_NAME = 'FairVillage - WIP'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

BROKER_URL = 'amqp://guest:guest@localhost:5672//'

"""
logging levels:
DEBUG: Low level system information for debugging purposes
INFO: General system information
WARNING: Information describing a minor problem that has occurred.
ERROR: Information describing a major problem that has occurred.
CRITICAL: Information describing a critical problem that has occurred.
"""
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'file': {
            'level': 'DEBUG',
            'filters': ['require_debug_false'],
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'debug.log'),
        },
    },
    'loggers': {
        'shell': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'wip.views': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# NLTK and other linguistic resources

NLTK_DATA_PATH = ''
LEXICONS = ''
CORPORA = ''
RESOURCES_ROOT = os.path.join(BASE_DIR, 'resources')
# morphit_path = "/Tecnica/CL/risorse/italiano/morph-it/morph-it.48/morph-it_048.txt"
morphit_filename = "morph-it_048.txt"
morphit_path = os.path.join(RESOURCES_ROOT, morphit_filename)
# tagger_filename = "itwac-1.2000000.biunigram.affix-2.simplified.pickle"
tagger_filename = "ITWAC-1.xml.pickle"



