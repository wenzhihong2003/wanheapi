# coding=utf-8
from __future__ import (unicode_literals, absolute_import, print_function)

from django.core.management.base import BaseCommand, CommandError

# from ... import md


class Command(BaseCommand):
    help = '获取股票代码表'

    def handle(self, *args, **options):
        # md.get_secmodels()

        self.stdout.write('成功获取股票代码表')
