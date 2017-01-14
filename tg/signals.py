# coding=utf-8
from __future__ import (unicode_literals, absolute_import, print_function)

from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction

from . import models

print('-------------------------------*******************')


@receiver(post_save, sender=models.UserInfo)
def post_save_userinfo(sender, instance, created, **kwargs):
    """
    创建一个用户时回调
    """
    if not created:
        return

    newuser = instance  # type: models.UserInfo
    models.UserStatistic.objects.create(user=newuser)


