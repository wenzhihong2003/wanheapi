from __future__ import unicode_literals

from django.apps import AppConfig


class TgConfig(AppConfig):
    name = 'tg'

    def ready(self):
        from . import signals
