# coding=utf-8
from __future__ import (unicode_literals, absolute_import)

from collections import OrderedDict
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination


class PageNumberPaginationWithPageSize(PageNumberPagination):
    """
    客户端可以指定每页数据的大小
    """
    page_size_query_param = 'page_size'
    page_size = 10
    max_page_size = 300

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('results', data)
        ]))
