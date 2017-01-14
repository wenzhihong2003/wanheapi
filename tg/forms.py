# coding=utf-8
from __future__ import (unicode_literals, absolute_import, print_function)
from django.db import models as djangomodels
from django.forms import forms
from django.contrib.auth import forms as authforms
from . import models


class UserChangeForm(authforms.UserChangeForm):
    def clean_email(self):
        email = self.cleaned_data.get("email", None)
        if self.instance.id and email:    # 修改用户
            cur_uid = self.instance.id    # 当前用户信息
            qs = models.UserInfo.objects.filter(~djangomodels.Q(id=cur_uid), email=email)
            if qs.exists():
                raise forms.ValidationError('邮件:{}已注册'.format(email), code='email_exist')
        return email

    def clean_mobile(self):
        mobile = self.cleaned_data.get("mobile", None)
        if self.instance.id and mobile:  # 修改用户
            cur_uid = self.instance.id   # 当前用户信息
            qs = models.UserInfo.objects.filter(~djangomodels.Q(id=cur_uid), mobile=mobile)
            if qs.exists():
                raise forms.ValidationError('手机号:{}已注册'.format(mobile), code='mobile_exist')
        return mobile

    class Meta(authforms.UserChangeForm.Meta):
        model = models.UserInfo


class UserCreationForm(authforms.UserCreationForm):
    class Meta(authforms.UserCreationForm):
        models = models.UserInfo