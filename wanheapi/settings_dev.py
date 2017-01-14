# coding=utf-8
# 这个做为本地测试开发时使用的 配置信息文件
from __future__ import absolute_import, print_function, unicode_literals
# 导入公共配置
from .settings_base import *

print('using dev enviment config file is : {}'.format(__file__))

DEBUG = True
DEBUG_PROPAGATE_EXCEPTIONS = True
ALLOWED_HOSTS = ['*']
# 设置模式为 debug模式
TEMPLATES[0]['OPTIONS']['debug'] = True
INTERNAL_IPS = ('127.0.0.1',)
USE_THOUSAND_SEPARATOR = True


# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'wanhe',
        'USER': 'root',
        'PASSWORD': 'root',
        'HOST': '127.0.0.1',
        'PORT': '3307',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 400,
        'KEY_PREFIX': 'gmadmin-default',
        'KEY_FUNCTION': memcached_hash_key
    },
}

# logger记录器
loggers = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'sqlfile': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'sql.log',
        },
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['sqlfile'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'wh': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
    },
}
# 合并 logging 配制, 用合并map的方式. http://www.pythoner.com/13.html
LOGGING = dict(LOGGING, **loggers)

# 在开发环境下, 只是把邮件内容打印在控制台上. 若要测试真实发邮件, 只需要把下面这行注释掉
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
