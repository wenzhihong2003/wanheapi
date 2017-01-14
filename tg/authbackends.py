# coding=utf-8
from __future__ import (unicode_literals, absolute_import, print_function)
from django.contrib.auth.backends import ModelBackend
from .models import UserInfo

"""
自定义用户认证的backend
"""


class MobileBackend(ModelBackend):
    """
    按手机号认证
    """
    def authenticate(self, username=None, password=None, **kwargs):
        if not username:
            return None

        rs = UserInfo.objects.filter(mobile=username)[:1]
        if rs:
            user = rs[0]
            return user if user.check_password(password) else None
        else:
            return None
