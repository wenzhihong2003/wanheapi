# coding=utf-8
from __future__ import (unicode_literals, absolute_import, print_function)

from django.conf.urls import url, include

from . import views as tg_views

from rest_framework.views import APIView

# 利用这个直接加入 url 映射
view_collect = []
urlpatterns = []
attrs = dir(tg_views)
for item in attrs:  # 得到的是名称 key
    att = getattr(tg_views, item)
    mymeta = getattr(att, 'mymeta') if hasattr(att, 'mymeta') else None
    if type(att) == type and issubclass(att, APIView) and mymeta:
        view_collect.append(att)
        urlpatterns.append(url(
            mymeta['myurl'], att.as_view(), name=mymeta['urlname']
        ))


def view_order(x, y):
    return getattr(x, 'mymeta')['seq'] - getattr(y, 'mymeta')['seq']

view_collect.sort(cmp=view_order)


urlpatterns.append(url('^$', tg_views.RootView.as_view(), name='apiroot'))

# urlpatterns = [
#     url(r'^login/$',
#         views.LoginView.as_view()),
#
#     url(r'^invest_adviser/4index/',
#         views.InvestAdviser4Index.as_view()),
#
#     url(r'^invest_adviser/search/',
#         views.InvestAdviserSearch.as_view()),
#
#     url(r'^invest_adviser/(?P<id>[\w-]+)/base_info/',
#         views.InvestAdviserBaseInfo.as_view()),
#
#     url(r'^invest_adviser/(?P<id>[\w-]+)/resume/',
#         views.InvestAdviserResume.as_view()),
#
#     url(r'^invest_adviser/(?P<id>[\w-])/invest_viewpoint/',
#         views.InvestAdviserInvestViewpoint.as_view()),
#
#     url(r'^invest_adviser/(?P<id>[\w-])/recommend_security/',
#         views.InvestAdviserRecommendSecurity.as_view()),
#
#     url(r'^invest_adviser/(?P<id>[\w-])/portfolio/',
#         views.InvestAdviserPortfolio.as_view()),
#
#     url(r'^security/4indexprice/',
#         views.Security4Indexprice.as_view()),
#
#     url(r'^news/4index/',
#         views.News4index.as_view()),
#
#     url(r'^news/type/',
#         views.NewsType.as_view()),
#
#     url(r'^news/(?P<id>[\w-]+)/',
#         views.NewsInfo.as_view()),
#
#     url(r'^recommend_security/4index/',
#         views.RecommendSecurity4index.as_view()),
#
#     url(r'^recommend_security/',
#         views.RecommendSecurity.as_view()),
#
#     url(r'^portfolio/search/',
#         views.PortfolioSearch.as_view()),
#
#     url(r'^portfolio/(?P<id>[\w-]+)/baseinfo/',
#         views.PortfolioBaseinfo.as_view()),
#
#     url(r'^portfolio/(?P<id>[\w-])/change_hold/',
#         views.PortfolioChangeHold.as_view()),
#
#     url(r'^portfolio/(?P<id>[\w-])/profit/',
#         views.PortfolioProfit.as_view()),
#
#     url(r'^portfolio/(?P<id>[\w-])/hold_secs/',
#         views.PortfolioHoldSecs.as_view()),
#
#     url(r'^ad/4index/',
#         views.Ad4index.as_view()),
#
#     url(r'^other/apply_job/',
#         views.OtherApplyJob.as_view()),
#
#     url(r'^other/hangqing/',
#         views.OtherHangqing.as_view()),
#
# ]
#
#
