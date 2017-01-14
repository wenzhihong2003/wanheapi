# coding=utf-8
from __future__ import (unicode_literals, absolute_import, print_function)

import logging
from calendar import timegm
from datetime import datetime

import requests
from django.contrib.auth.models import User
from django.utils import crypto
from rest_framework.settings import api_settings as drf_api_settings
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework_jwt.settings import api_settings as jwt_api_settings
from typing import Union, Dict, List, Tuple, Any, Iterable

logger = logging.getLogger('wh')


# <editor-fold desc="用于djangorestframework-jwt">
def jwt_payload_handler(user):
    # type: (User) -> dict
    payload = {
        'user_id': user.pk,
        'email': user.email,
        'username': user.username,
        'exp': datetime.utcnow() + jwt_api_settings.JWT_EXPIRATION_DELTA
    }

    if jwt_api_settings.JWT_ALLOW_REFRESH:
        payload['orig_iat'] = timegm(
            datetime.utcnow().utctimetuple()
        )

    return payload


def jwt_get_user_id_from_payload_handler(payload):
    # type: (dict) -> int
    return payload.get('user_id')


def jwt_get_username_from_payload_handler(payload):
    # type: (dict) -> Union[str, unicode]
    return payload.get('username')


def jwt_response_payload_handler(token, user=None, request=None):
    return {
        'jwttoken': token,
    }
# </editor-fold>


def first_not_empty_value(obj, attrs):
    """
    取第一个不为空的属性值
    """
    for attr in attrs:
        v = getattr(obj, attr)
        if v:
            return v
    return None


def url2short(url):
    # type: (str) -> str
    """
    使用sina的短地址服务
    """
    r = requests.get('http://api.t.sina.com.cn/short_url/shorten.json?source=392971908&url_long=' + url)
    return r.json()[0]['url_short']


def dictfetchall(cursor):
    """
    Returns all rows from a cursor as a dict
    """
    desc = cursor.description
    rows = cursor.fetchall()
    if rows:
        return [
            dict(zip([col[0] for col in desc], row))
            for row in rows
            ]
    else:
        return []


def dictfetchone(cursor):
    desc = cursor.description
    row = cursor.fetchone()
    return dict(zip([col[0] for col in desc], row)) if row else {}


def get_random_string(length=6, allowed_chars='abcdefghijklmnopqrstuvwxyz23456789'):
    return crypto.get_random_string(length, allowed_chars)


def get_random_verifycode(length=6, allowed_chars='1234567890'):
    return crypto.get_random_string(length, allowed_chars)


def securitycode_key(phone):
    return "sc_{}".format(phone)


# <editor-fold desc="用于view的工具函数">
def ok_data(msg=None, data=None):
    okmsg = '成功' if msg is None else msg
    return dict(success=True, msg=okmsg, data=data) if data else dict(success=True, msg=okmsg, data={})


def fail_data(msg=None, data=None):
    failmsg = '失败' if msg is None else msg
    return dict(success=False, msg=failmsg, data=data) if data else dict(success=False, msg=failmsg, data={})


def extend_response(resp, ok_msg='成功', fail_msg='失败'):
    # type: (Response, Union[str, unicode], Union[str, unicode]) -> Response
    """
    把response扩展成已定义好的格式
    统一使用 http 200 状态码
    成功:
    {
      "success": true,
      "msg": "成功",
      "data": {}
    }
    失败:
    {
      "success": false,
      "msg": "失败",
      "data": {}
    }
    """
    if resp.status_code == status.HTTP_200_OK:
        resp.data = ok_data(msg=ok_msg, data=resp.data)
    elif resp.status_code == status.HTTP_400_BAD_REQUEST:
        resp.status_code = status.HTTP_200_OK
        resp.data = fail_data(msg=fail_msg, data=resp.data)
    return resp

# 不归属于字段的 ValidationError 的 key值
NON_FIELD_ERRORS_KEY = drf_api_settings.NON_FIELD_ERRORS_KEY


def fail_response_withseria(serializer, nodata=True):
    # type: (serializers.Serializer, bool) -> Response
    """
    把 serializer.errors 里的信息提取到response的msg输出
    如果有 NON_FIELD_ERRORS_KEY 存在, 则直接到msg. 不然的话就提取第1个出错的信息
    """
    errors = serializer.errors
    if NON_FIELD_ERRORS_KEY in errors:
        data = {} if nodata else errors
        return Response(fail_data(
            msg=errors.pop(NON_FIELD_ERRORS_KEY)[0],
            data=data)
        )
    else:
        key, value = errors.iteritems().next()
        label = None
        if key in serializer.fields:
            label = serializer.fields[key].label
        if not label:
            label = key

        data = {} if nodata else errors
        return Response(fail_data(
            msg='{}:{}'.format(label, value[0]),
            data=data
        ))

# </editor-fold>
