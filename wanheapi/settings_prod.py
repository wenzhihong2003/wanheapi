# coding=utf-8
# 这个做为生产环境的配置信息使用
from __future__ import (unicode_literals, absolute_import, print_function)
from .settings_base import *

print('using prod enviment config file is : '.format(__file__))

ALLOWED_HOSTS = ['*']
DEBUG = False
# 设置模式为 debug模式
TEMPLATES[0]['OPTIONS']['debug'] = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'wanhe',
        'USER': 'xxxx',
        'PASSWORD': 'xxxxx',
        'HOST': 'xxxxxxxxxxxxxxx',
        'PORT': '3306',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 400,
        'KEY_PREFIX': 'wanheapi',
        'KEY_FUNCTION': memcached_hash_key
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
