# coding=utf-8
from __future__ import (unicode_literals, absolute_import)

from rest_framework.request import Request
from rest_framework.authentication import SessionAuthentication
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

class UnsafeSessionAuthentication(SessionAuthentication):
    """
    指定参数(__nocheck)时,不进行csrf进行检查
    """
    def authenticate(self, request):
        """
        Returns a `User` if the request session currently has a logged in user.
        Otherwise returns `None`.
        """

        # Get the underlying HttpRequest object
        nocsrf = request.data.get('__nocheck', '') or request.query_params.get('__nocheck', '')
        # 为了简化调用, 修改django-rest-framework的session认证要验csrf. 直接改成不进行验证了. 如果要修改, 直接把下面一行去掉即可. 这样在调用时要加上__nocheck=true
        nocsrf = 'true'
        request = request._request
        user = getattr(request, 'user', None)

        # Unauthenticated, CSRF validation not required
        if not user or not user.is_active:
            return None

        if not nocsrf:
            self.enforce_csrf(request)

        # CSRF passed with authenticated user
        return (user, None)


class JSONWebTokenAuthenticationUri(JSONWebTokenAuthentication):
    """
    在原功能的基础上, 增加从uri上获取jwttoken
    """
    def get_jwt_value(self, request):
        jwt_value = super(JSONWebTokenAuthenticationUri, self).get_jwt_value(request)
        if not jwt_value:
            django_request = request._request if isinstance(request, Request) else request
            jwt_value = django_request.GET.get('jwttoken', '').strip()
            if not jwt_value:
                return None

        return jwt_value
