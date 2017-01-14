# coding=utf-8
from __future__ import (unicode_literals, absolute_import, print_function)

import arrow
import jwt
import random
from datetime import timedelta, datetime
from django.utils import timezone
from django.contrib.auth import authenticate, update_session_auth_hash
from django.core.cache import cache
from django.db import transaction
from django.db import models as djangomodels
from django.conf import settings

from rest_framework.compat import set_rollback
from rest_framework.settings import api_settings as drf_api_settings
from rest_framework.decorators import permission_classes
from rest_framework.request import Request
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.views import APIView, exception_handler
from rest_framework.generics import (GenericAPIView, CreateAPIView, ListAPIView, RetrieveAPIView, DestroyAPIView,
                                     UpdateAPIView, ListCreateAPIView, RetrieveUpdateAPIView, RetrieveDestroyAPIView,
                                     RetrieveUpdateDestroyAPIView, get_object_or_404)
from rest_framework import (status, exceptions, serializers, permissions, renderers)
from rest_framework_jwt.settings import api_settings as jwt_api_settings

from . import utils, serializers as tg_serializers, models
from .utils import ok_data, fail_data, fail_response_withseria, securitycode_key

apiseq = 1


def my_exception_handler(exc, context):
    """
    处理exception
    """
    if isinstance(exc, exceptions.ValidationError):
        set_rollback()
        msg = '有错误了'
        if isinstance(exc.detail, list):
            msg = exc.detail[0]
        elif isinstance(exc.detail, dict):
            msg = exc.popitem()[1]
        else:
            msg = exc.detail
        return Response(fail_data(msg=msg))

    return exception_handler(exc, context)


class RootView(APIView):
    """
    api根入口, 展示所有可用的api的url
    """
    permission_classes = (permissions.AllowAny,)
    renderer_classes = (renderers.TemplateHTMLRenderer,)

    def get(self, request, format=None):
        from . import urls

        urldatas = []
        for v in urls.view_collect:
            demourl = reverse(v.mymeta['urlname'], kwargs=v.mymeta['urlkwargs'], request=request)
            if v.mymeta.get('queryparam', ''):
                demourl += '?' + v.mymeta['queryparam']

            item = {
                'doc': v.__doc__.strip('\n').split()[0],
                'demourl': demourl
            }
            urldatas.append(item)

        return Response({'urldatas': urldatas}, template_name='api-index.html')


jwt_payload_handler = jwt_api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = jwt_api_settings.JWT_ENCODE_HANDLER
jwt_decode_handler = jwt_api_settings.JWT_DECODE_HANDLER


class JSONWebTokenSerializer(serializers.Serializer):
    username = serializers.CharField(label='用户名')
    password = serializers.CharField(label='密码')

    def validate(self, attrs):
        # type: (dict) -> dict
        user = authenticate(username=attrs['username'], password=attrs['password'])  # type: models.UserInfo
        if user:
            if not user.is_active:
                raise serializers.ValidationError('用户还没有激活')

            payload = jwt_payload_handler(user)
            return {
                'token': jwt_encode_handler(payload),
                'exp': payload['exp'],
                'user': user,
            }
        else:
            raise serializers.ValidationError('用户名或者密码错误')


class LoginView(GenericAPIView):
    """
    用户登陆
    """
    serializer_class = JSONWebTokenSerializer
    permission_classes = ()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)  # type: JSONWebTokenSerializer
        if serializer.is_valid():
            user = serializer.validated_data.get('user') or request.user  # type: models.UserInfo
            token = serializer.validated_data.get('token')
            exp = serializer.validated_data.get('exp')
            data = {
                'jwttoken': token,
                'exp': exp,
                'user': tg_serializers.CurUserInfoSerializer(user, context=self.get_serializer_context()).data
            }
            return Response(ok_data(data=data))
        else:
            return fail_response_withseria(serializer)
LoginView.mymeta = {
    'myurl': r'^login/$',
    'urlname': 'UrlLoginView',
    'urlkwargs': {},
    'seq': apiseq,
}
apiseq += 1


class RefreshToken(GenericAPIView):
    """
    根据已有的token,刷新获取新的token(需要jwttoekn)
    """
    class RefreshTokenSerializer(serializers.Serializer):
        # jwttoken = serializers.CharField(read_only=True)
        jwttoken = serializers.ReadOnlyField()
        user = tg_serializers.CurUserInfoSerializer(read_only=True)
        exp = serializers.ReadOnlyField()

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = RefreshTokenSerializer

    def post(self, request, *args, **kwargs):
        user = request.user
        payload = jwt_payload_handler(user)
        data = {
            'jwttoken': jwt_encode_handler(payload),
            'user': user,
            'exp': payload['exp'],
        }
        seria = self.get_serializer(data)
        return Response(ok_data(data=seria.data))
RefreshToken.mymeta = {
    'myurl': r'^refresh_token/$',
    'urlname': 'UrlRefreshToken',
    'urlkwargs': {},
    'seq': apiseq,
}
apiseq += 1


class CheckJwtToken(GenericAPIView):
    """
    检查jwttoken
    """
    class CheckJwtTokenSerializer(serializers.Serializer):
        token = serializers.CharField()

        # noinspection PyMethodMayBeStatic
        def validate_token(self, value):
            msg = None
            try:
                payload = jwt_decode_handler(value)
            except jwt.ExpiredSignature:
                msg = 'token过期'
            except jwt.DecodeError:
                msg = 'token编码错误'
            if msg:
                raise exceptions.ValidationError(msg)
            return value

    permission_classes = (permissions.AllowAny,)
    serializer_class = CheckJwtTokenSerializer

    def post(self, request, *args, **kwargs):
        seria = self.get_serializer(data=request.data)
        if seria.is_valid():
            return Response(ok_data(msg='token有效'))
        else:
            return fail_response_withseria(seria)
CheckJwtToken.mymeta = {
    'myurl': r'^check_jwttoken/$',
    'urlname': 'UrlCheckJwtToken',
    'urlkwargs': {},
    'seq': apiseq,
}
apiseq += 1


class InvestAdviser4Index(GenericAPIView):
    """
    首页推荐牛投
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = tg_serializers.InvestAdviserBaseInfoSerializer

    def get_queryset(self):
        # fixme 获取首页推荐的牛投ids
        ids = range(1, 10)  # 投顾ids
        qs = models.InvestAdviserInfo.objects.filter(
            user_id__in=ids
        ).prefetch_related(
            'user', 'user__investadviserkpi'
        )[:3]
        return qs

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
InvestAdviser4Index.mymeta = {
    'myurl': r'^invest_adviser/4index/$',
    'urlname': 'UrlInvestAdviser4Index',
    'urlkwargs': {},
    'seq': apiseq,
}
apiseq += 1


class InvestAdviserSearch(GenericAPIView):
    """
    按分类获取牛投顾列表
    type	str	搜索类别:1:综合排名; 2:荐股成功率; 4:累计收益率
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = tg_serializers.InvestAdviserBaseInfoSerializer

    def get_queryset(self):
        typev = self.request.query_params.get('type', None)
        qs = models.InvestAdviserInfo.objects.all()
        if typev == '1':
            pass
            # qs = qs.order_by('-user__investadviserkpi__success_ratio')
        elif typev == '2':
            qs = qs.order_by('user__investadviserkpi__success_ratio')
        elif typev == '4':
            qs = qs.order_by('-user__investadviserkpi__accumulate_profit_ratio')
        return qs

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        pagedata = self.get_paginated_response(serializer.data).data
        if request.user.is_authenticated:
            pagedata['results'].sort(key=lambda x: x['is_follow'], reverse=True)
            return Response(ok_data(data={'advisers': pagedata}))
        else:
            return Response(ok_data(data={'advisers': serializer.data}))
InvestAdviserSearch.mymeta = {
    'myurl': r'^invest_adviser/search/$',
    'urlname': 'UrlInvestAdviserSearch',
    'urlkwargs': {},
    'seq': apiseq,
}
apiseq += 1


class InvestAdviserBaseInfo(GenericAPIView):
    """
    投顾基本信息
    """
    lookup_field = 'user_id'
    lookup_url_kwarg = 'pk'
    permission_classes = (permissions.AllowAny,)
    serializer_class = tg_serializers.InvestAdviserBaseInfoSerializer
    queryset = models.InvestAdviserInfo.objects.all()

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(ok_data(data=serializer.data))
InvestAdviserBaseInfo.mymeta = {
    'myurl': r'^invest_adviser/(?P<pk>[\w-]+)/base_info/$',
    'urlname': 'UrlInvestAdviserBaseInfo',
    'urlkwargs': {'pk': '4'},
    'seq': apiseq,
}
apiseq += 1


class InvestAdviserResume(APIView):
    """
    投顾个人简介
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        pk = int(self.kwargs.get('pk'))
        obj = get_object_or_404(models.InvestAdviserInfo.objects.filter(user_id=pk))
        data = {
            'id': pk,
            'experience': obj.experience,
            'good_at': obj.good_at
        }

        return Response(ok_data(data=data))
InvestAdviserResume.mymeta = {
    'myurl': r'^invest_adviser/(?P<pk>[\w-]+)/resume/$',
    'urlname': 'InvestAdviserResume',
    'urlkwargs': {'pk': '4'},
    'seq': apiseq,
}
apiseq += 1


class InvestAdviserInvestViewpoint(GenericAPIView):
    """
    投顾投资观点(分页)
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = tg_serializers.InvestViewpointSerializer

    def get_serializer_context(self):
        context = super(InvestAdviserInvestViewpoint, self).get_serializer_context()
        context.update(adviser_self=True)   # 指明是投顾自身,不要序列化投顾信息
        return context

    def get_queryset(self):
        return models.InvestViewpoint.objects.filter(
            owner=self.kwargs['pk']
        ).order_by(
            '-pub_daytime'
        )

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        pagedata = self.get_paginated_response(serializer.data).data
        return Response(ok_data(data={'viewpoints': pagedata}))
InvestAdviserInvestViewpoint.mymeta = {
    'myurl': r'^invest_adviser/(?P<pk>[\w-]+)/invest_viewpoint/$',
    'urlname': 'UrlInvestAdviserInvestViewpoint',
    'urlkwargs': {'pk': '4'},
    'seq': apiseq,
}
apiseq += 1


class InvestViewpointInfo(GenericAPIView):
    """
    投资观点详情
    """
    permission_classes = (permissions.AllowAny,)
    renderer_classes = (renderers.TemplateHTMLRenderer,)

    def get(self, request, *args, **kwargs):
        viewpoint = get_object_or_404(models.InvestViewpoint.objects.all(), pk=kwargs['pk'])
        return Response({'vp': viewpoint}, template_name='tg/investviewpointinfo.html')

InvestViewpointInfo.mymeta = {
    'myurl': r'^invest_viewpoint_info/(?P<pk>[\w-]+)/$',
    'urlname': 'UrlInvestViewpointInfo',
    'urlkwargs': {'pk': '1'},
    'seq': apiseq,
}
apiseq += 1


class InvestAdviserRecommendSecurity(GenericAPIView):
    """
    投顾推荐股票 (分页)
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = tg_serializers.RecommendSecuritySerializer

    def get_serializer_context(self):
        context = super(InvestAdviserRecommendSecurity, self).get_serializer_context()
        context.update(adviser_self=True)   # 指明是投顾自身,不要序列化投顾信息
        return context

    def get_queryset(self):
        return models.InvestRecommendSecurity.objects.filter(
            owner=self.kwargs['pk']
        ).order_by(
            '-ctime'
        )

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        pagedata = self.get_paginated_response(serializer.data).data
        resultdata = pagedata['results']
        secids = [item['sec_idxid'] for item in resultdata]  # SZSE.000001 这样的格式
        # sechqmap = md.get_last_ticks(secids)
        sechqmap = [{}]
        for item in resultdata:
            item.update(**sechqmap.get(item['sec_idxid'], {}))
        return Response(ok_data(data={'recommend_secs':pagedata}))
InvestAdviserRecommendSecurity.mymeta = {
    'myurl': r'^invest_adviser/(?P<pk>[\w-]+)/recommend_security/$',
    'urlname': 'UrlInvestAdviserRecommendSecurity',
    'urlkwargs': {'pk': '4'},
    'seq': 7,
}


class InvestAdviserPortfolio(GenericAPIView):
    """
    投顾投资组合 (分页)
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = tg_serializers.PortfolioBaseinfoSerializer

    def get_serializer_context(self):
        context = super(InvestAdviserPortfolio, self).get_serializer_context()
        context.update(adviser_self=True)   # 指明是投顾自身,不要序列化投顾信息
        return context

    def get_queryset(self):
        return models.PortfolioBaseInfo.objects.filter(
            owner=self.kwargs['pk']
        ).order_by(
            '-ctime'
        )

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        pagedata = self.get_paginated_response(serializer.data).data
        return Response(ok_data(data={'portfolios': pagedata}))
InvestAdviserPortfolio.mymeta = {
    'myurl': r'^invest_adviser/(?P<pk>[\w-]+)/portfolio/$',
    'urlname': 'UrlInvestAdviserPortfolio',
    'urlkwargs': {'pk': '4'},
    'seq': apiseq
}
apiseq += 1


class Security4Indexprice(GenericAPIView):
    """
    首页指数价格信息
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        secids = ['SHSE.000001', 'SZSE.399001', 'SZSE.399005', 'SZSE.399006']  # 要查询行情的代码
        sechqmap = [{}]
        return Response(ok_data(data={'secs': sechqmap.values()}))
Security4Indexprice.mymeta = {
    'myurl': r'^security/4indexprice/$',
    'urlname': 'UrlSecurity4Indexprice',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class News4index(GenericAPIView):
    """
    首页推荐资讯
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        data = {
            "success": True,
            "msg": "说明信息",
            "data": {
                "news": [
                    {
                        "id": 12,
                        "title": "标题",
                        "digest": "fsdafasdfsdfasd",
                        "pub_daytime": "2016-03-10 10:10:10",
                        "sub_picture": "http://mypic.com/1.png",
                        "topics": "今日头条",
                    }
                ]
            }
        }
        return Response(data)
News4index.mymeta = {
    'myurl': r'^news/4index/$',
    'urlname': 'UrlNews4index',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class NewsType(GenericAPIView):
    """
    按分类获取资讯列表(分页)
    type	str	类别:1:市场要闻; 2:市场评论
    """
    class NewsSerializer(serializers.ModelSerializer):
        html5 = serializers.SerializerMethodField()

        def get_html5(self, obj):
            return reverse('UrlNewsInfo', kwargs={'pk': obj.id}, request=self.context['request'])

        class Meta:
            model = models.News
            exclude = ('content',)

    permission_classes = (permissions.AllowAny,)
    serializer_class = NewsSerializer

    def get_queryset(self):
        t = self.request.query_params.get('type', '0')
        queryset = models.News.objects.all().order_by('-pub_daytime')
        if t == '1':
            queryset = queryset.filter(id__lt=3)
        elif t == '2':
            queryset = queryset.filter(id__gt=3)

        return queryset

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        pagedata = self.get_paginated_response(serializer.data).data
        pagedata['result'] = pagedata['results']  # fixme 这句是因为之前搞错了, 写成result
        return Response(ok_data(data={'news': pagedata}))
NewsType.mymeta = {
    'myurl': r'^news/type/$',
    'urlname': 'UrlNewsType',
    'urlkwargs': {},
    'seq': apiseq,
}
apiseq += 1


class NewsInfo(GenericAPIView):
    """
    资讯详情
    """
    permission_classes = (permissions.AllowAny,)
    renderer_classes = (renderers.TemplateHTMLRenderer,)

    def get(self, request, *args, **kwargs):
        news = get_object_or_404(models.News.objects.all(), pk=kwargs['pk'])
        return Response({'news': news}, template_name='tg/newsinfo.html')
NewsInfo.mymeta = {
    'myurl': r'^newsinfo/(?P<pk>[\d]+)/$',
    'urlname': 'UrlNewsInfo',
    'urlkwargs': {'pk': '2134123'},
    'seq': apiseq,
}
apiseq += 1


class RecommendSecurity4index(GenericAPIView):
    """
    首页推荐牛股
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = tg_serializers.RecommendSecuritySerializer

    def get_queryset(self):
        return models.InvestRecommendSecurity.objects \
            .filter(ctime__gte=timezone.now() - timedelta(days=60))\
            .prefetch_related('owner')\
            .order_by('-accumulate_ratio')[:3]

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        resultdata = serializer.data
        secids = [item['sec_idxid'] for item in resultdata]  # SZSE.000001 这样的格式
        sechqmap = [{}]
        for item in resultdata:
            item.update(**sechqmap.get(item['sec_idxid'], {}))
        return Response(ok_data(data={'recommend_secs': resultdata}))
RecommendSecurity4index.mymeta = {
    'myurl': r'^recommend_security/4index/$',
    'urlname': 'UrlRecommendSecurity4index',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class RecommendSecurity(GenericAPIView):
    """
    牛股列表 (分页)
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = tg_serializers.RecommendSecuritySerializer

    def get_queryset(self):
        return models.InvestRecommendSecurity.objects \
            .filter(ctime__gte=timezone.now() - timedelta(days=60))\
            .prefetch_related('owner')\
            .order_by('-accumulate_ratio')

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        pagedata = self.get_paginated_response(serializer.data).data
        resultdata = pagedata['results']
        secids = [item['sec_idxid'] for item in resultdata]  # SZSE.000001 这样的格式
        sechqmap = [{}]
        for item in resultdata:
            item.update(**sechqmap.get(item['sec_idxid'], {}))
        return Response(ok_data(data={'recommend_secs': pagedata}))
RecommendSecurity.mymeta = {
    'myurl': r'^recommend_security/$',
    'urlname': 'UrlRecommendSecurity',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class PortfolioSearch(GenericAPIView):
    """
    按分类获取牛组合列表(分页)
    type	str	搜索类别:1:当日收益; 2:周收益; 3:月收益; 4:累计收益
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = tg_serializers.PortfolioBaseinfoSerializer

    def get_queryset(self):
        typev = self.request.query_params.get('type', None)
        qs = models.PortfolioBaseInfo.objects.all().prefetch_related('owner')
        if typev == '1':
            qs = qs.order_by('-curdate_ratio')
        elif typev == '2':
            qs = qs.order_by('-week_ratio')
        elif typev == '3':
            qs = qs.order_by('-month_ratio')
        elif typev == '4':
            qs = qs.order_by('-accumulate_ratio')

        return qs

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        pagedata = self.get_paginated_response(serializer.data).data
        resultdata = pagedata['results']
        if self.request.user.is_authenticated:
            resultdata.sort(key=lambda x: x['is_subscribe'], reverse=True)

        return Response(ok_data(data={'portfolios': pagedata}))
PortfolioSearch.mymeta = {
    'myurl': r'^portfolio/search/$',
    'urlname': 'UrlPortfolioSearch',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class PortfolioBaseinfo(GenericAPIView):
    """
    牛组合基本信息
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = tg_serializers.PortfolioBaseinfoSerializer
    queryset = models.PortfolioBaseInfo.objects.all()

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(ok_data(data=serializer.data))
PortfolioBaseinfo.mymeta = {
    'myurl': r'^portfolio/(?P<pk>[\w-]+)/baseinfo/$',
    'urlname': 'UrlPortfolioBaseinfo',
    'urlkwargs': {'pk': '4'},
    'seq': apiseq
}
apiseq += 1


class PortfolioChangeHold(GenericAPIView):
    """
    牛组合最近调仓(分页)
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        data = {
            "success": True,
            "msg": "说明信息",
            "data": {
                "holds": {
                    "count": 300,
                    "result": [
                        {
                            "id": 1234,
                            "type": "buy",
                            "sec_id": "000001",
                            "sec_name": "平安银行",
                            "trade_price": 8.06,
                            "trade_time": "2016-09-26 14:57:00",
                            "profit_ratio": 52.89,
                            "position_change": 76.56
                        }
                    ]
                }
            }
        }
        return Response(data)
PortfolioChangeHold.mymeta = {
    'myurl': r'^portfolio/(?P<id>[\w-]+)/change_hold/$',
    'urlname': 'UrlPortfolioChangeHold',
    'urlkwargs': {'id': '1234'},
    'seq': apiseq
}
apiseq += 1


class PortfolioProfit(GenericAPIView):
    """
    牛组合收益走势
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        result = []
        baseline_result = []
        start = datetime(2016, 9, 5, 9, 30)
        end = datetime(2016, 10, 31, 15, 00)
        for idx, item in enumerate(arrow.Arrow.range('day', start, end)):
            v = random.randrange(10, 50, 2)
            result.append({
                'id': idx + 10,
                'trade_time': item.format('YYYY-MM-DD HH:mm:ss'),
                'profit_ratio': v,
            })
            baseline_result.append({
                'id': idx + 20,
                'trade_time': item.format('YYYY-MM-DD HH:mm:ss'),
                'profit_ratio': v + 5
            })


        data = {
            "success": True,
            "msg": "说明信息",
            "data": {
                "holds": {
                    "count": 300,
                    'sec_name': '牛投寒风组合2',
                    "result": result,
                },
                "baselines": {
                    'sec_id': 'szsz.000001',
                    'sec_name': '沪深300',
                    'result': baseline_result
                }
            }
        }
        return Response(data)
PortfolioProfit.mymeta = {
    'myurl': r'^portfolio/(?P<id>[\w-]+)/profit/$',
    'urlname': 'UrlPortfolioProfit',
    'urlkwargs': {'id': '1234'},
    'seq': apiseq
}
apiseq += 1


class PortfolioHoldSecs(GenericAPIView):
    """
    牛组合股票持仓(分页)
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        data = {
            "success": True,
            "msg": "说明信息",
            "data": {
                "holds": {
                    "count": 300,
                    "result": [
                        {
                            "id": 1234,
                            "sec_id": "000001",
                            "sec_name": "平安银行",
                            "position": 9.25,
                            "cur_price": 25.27,
                            "cost": 21.22,
                            "profit_ratio": 21.22,
                        }
                    ]
                }
            }
        }
        return Response(data)
PortfolioHoldSecs.mymeta = {
    'myurl': r'^portfolio/(?P<id>[\w-]+)/hold_secs/$',
    'urlname': 'UrlPortfolioHoldSecs',
    'urlkwargs': {'id': '1234'},
    'seq': apiseq
}
apiseq += 1


class Ad4index(GenericAPIView):
    """
    首页广告
    """
    class AdSerializer(serializers.ModelSerializer):
        class Meta:
            model = models.Ad

    permission_classes = (permissions.AllowAny,)
    serializer_class = AdSerializer
    queryset = models.Ad.objects.filter(isvalid=True).order_by('-ctime', '-id')[0:4]

    def get(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        seria = self.get_serializer(qs, many=True)
        return Response(ok_data(data={'ads': seria.data}))


Ad4index.mymeta = {
    'myurl': r'^ad/4index/$',
    'urlname': 'UrlAd4index',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class OtherApplyJobGet(GenericAPIView):
    """
    投顾招聘(申请投顾)(展示页面)
    """
    permission_classes = (permissions.AllowAny,)
    renderer_classes = (renderers.TemplateHTMLRenderer,)

    def get(self, request, *args, **kwargs):
        return Response(template_name='tg/ad/apply_job_get.html')
OtherApplyJobGet.mymeta = {
    'myurl': r'^other/apply_job_get/$',
    'urlname': 'UrlOtherApplyJobGet',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class OtherApplyJobPolicy(GenericAPIView):
    """
    投顾政策
    """
    permission_classes = (permissions.AllowAny,)
    renderer_classes = (renderers.TemplateHTMLRenderer,)

    def get(self, request, *args, **kwargs):
        return Response(template_name='tg/ad/apply_job_policy.html')
OtherApplyJobPolicy.mymeta = {
    'myurl': r'^other/apply_job_policy/$',
    'urlname': 'UrlOtherApplyJobPolicy',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class OtherApplyJob(GenericAPIView):
    """
    投顾招聘(申请投顾)(提交请求)
    """
    class OtherApplyJobSerializer(serializers.ModelSerializer):
        class Meta:
            model = models.ApplyAdviserJob
            read_only_fields = ('status', )

    permission_classes = (permissions.AllowAny,)
    serializer_class = OtherApplyJobSerializer

    def post(self, request, *args, **kwargs):
        seri = self.get_serializer(data=request.data)
        if seri.is_valid():
            seri.save()
            return Response(data=ok_data())
        else:
            return fail_response_withseria(seri)
OtherApplyJob.mymeta = {
    'myurl': r'^other/apply_job/$',
    'urlname': 'UrlOtherApplyJob',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class OtherHangqing(GenericAPIView):
    """
    获取指定一批股票的行情
    sec_ids	str	多个股票代码. 如 SHSE.600000,SHSE.600004
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        sec_ids = self.request.query_params.get('sec_ids', 'SHSE.600000')
        sechqmap = [{}]
        return Response(ok_data(data={'secs': sechqmap.values()}))
OtherHangqing.mymeta = {
    'myurl': r'^other/hangqing/$',
    'urlname': 'UrlOtherHangqing',
    'urlkwargs': {},
    'queryparam': 'sec_ids=SHSE.600000,SHSE.600004',
    'seq': apiseq
}
apiseq += 1


class CurUserInfo(GenericAPIView):
    """
    当前登陆用户信息(需要jwttoken)
    gender: 1:男, 2:女, 3:保密
    gender_cn: 中文意思
    """
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = tg_serializers.CurUserInfoSerializer

    def get(self, request, *args, **kwargs):
        user = request.user  # type: models.UserInfo
        ser = self.get_serializer(user)
        return Response(ok_data(data=ser.data))
CurUserInfo.mymeta = {
    'myurl': r'^cur_user_info/$',
    'urlname': 'UrlCurUserInfo',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class UserUpdateAvatar(GenericAPIView):
    """
    用户修改头像(需要jwttoekn)
    返回用户的头像地址
    """
    class UserUpdateAvatarSerializer(serializers.Serializer):
        avatar = serializers.ImageField()

        def create(self, validated_data):
            curuser = self.context['request'].user
            curuser.avatar = validated_data['avatar']
            curuser.save(force_update=True, update_fields=('avatar',))
            return {
                'avatar': curuser.avatar
            }

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserUpdateAvatarSerializer

    def post(self, request, *args, **kwargs):
        seria = self.get_serializer(data=self.request.data)  # type: UserUpdateAvatar.UserUpdateAvatarSerializer
        if seria.is_valid():
            seria.save()
            return Response(ok_data(data=seria.data))
        else:
            return fail_response_withseria(seria)
UserUpdateAvatar.mymeta = {
    'myurl': r'^user/updateavatar/$',
    'urlname': 'urlUserUpdateAvatar',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class UserUpdateBaseInfo(GenericAPIView):
    """
    用户修改基本信息(昵称,性别)(需要jwttoekn)
    """
    class UserUpdateBaseInfoSerializer(serializers.ModelSerializer):
        class Meta:
            model = models.UserInfo
            fields = ('nick_name', 'gender',)

        def update(self, instance, validated_data):
            for attr, value in validated_data.items():
                if value:
                    setattr(instance, attr, value)
            instance.save()

            return instance

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserUpdateBaseInfoSerializer

    def post(self, request, *args, **kwargs):
        seria = self.get_serializer(request.user, data=request.data, partial=True)
        if seria.is_valid():
            seria.save()
            return Response(data=ok_data())
        else:
            return fail_response_withseria(seria)

UserUpdateBaseInfo.mymeta = {
    'myurl': r'^user/updatebaseinfo/$',
    'urlname': 'urlUserUpdateBaseInfo',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class UserSetPasswd(GenericAPIView):
    """
    用户修改密码.(需要jwttoekn)
    """
    class UserSetPasswdSerializer(serializers.Serializer):
        old_passwd = serializers.CharField(max_length=30)
        new_passwd = serializers.CharField(max_length=30)

        def update(self, instance, validated_data):
            curuser = instance  # type: models.UserInfo
            if not curuser.check_password(validated_data['old_passwd']):
                raise exceptions.ValidationError('旧密码不对')

            curuser.set_password(validated_data['new_passwd'])
            curuser.save(force_update=True, update_fields=('password', ))
            return instance

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSetPasswdSerializer

    def post(self, request, *args, **kwargs):
        seria = self.get_serializer(request.user, data=request.data)
        if seria.is_valid():
            seria.save()
            update_session_auth_hash(request, request.user)
            return Response(data=ok_data(msg='修改密码成功'))
        else:
            return fail_response_withseria(seria)

UserSetPasswd.mymeta = {
    'myurl': r'^user/setpasswd/$',
    'urlname': 'urlUserSetPasswd',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class RebindMobile(GenericAPIView):
    """
    绑定手机号.(需要jwttoekn)
    如果原手机号为空则不需要原手机号,否则的话,一定需要原手机号
    """
    class RebindMobileSerializer(serializers.Serializer):
        old_mobile = serializers.CharField(max_length=30, required=False, help_text='有旧手机号,则要输入')
        new_mobile = serializers.CharField(max_length=30)
        security_code = serializers.CharField(max_length=30)

        def update(self, instance, validated_data):
            curuser = instance  # type: models.UserInfo
            old_mobile = validated_data.get('old_mobile', None)
            new_mobile = validated_data.get('new_mobile', None)
            security_code = validated_data.get('security_code', '')
            if curuser.mobile:
                if old_mobile:
                    if old_mobile.strip() != curuser.mobile.strip():
                        raise exceptions.ValidationError('旧手机号不对')
                else:
                    raise exceptions.ValidationError('请输入旧手机号')

            if cache.get(securitycode_key(new_mobile)) != security_code:
                # fixme 验证码错误一次是否要验证码作废, 重新发送?? 先简单处理, 不作废
                raise exceptions.ValidationError('验证码错误')
            curuser.mobile = new_mobile
            curuser.save(force_update=True, update_fields=('mobile',))
            cache.delete(securitycode_key(new_mobile))
            return instance

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = RebindMobileSerializer

    def post(self, request, *args, **kwargs):
        seria = self.get_serializer(request.user, data=request.data)
        if seria.is_valid():
            seria.save()
            return Response(ok_data(msg='重新绑定手机号成功'))
        else:
            return fail_response_withseria(seria)
RebindMobile.mymeta = {
    'myurl': r'^user/rebindmobile/$',
    'urlname': 'urlRebindMobile',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class FollowInvestAdviser(GenericAPIView):
    """
    关注投顾(需要jwttoken).加上?action=cancel 表示取消关注
    """
    class FollowInvestAdviserSerializer(serializers.Serializer):
        ids = serializers.CharField(label='投顾id', help_text='如果是多个话, 则 `1,2,3` 这样的格式')

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = FollowInvestAdviserSerializer

    def post(self, request, *args, **kwargs):
        seria = self.get_serializer(data=request.data)
        if seria.is_valid():
            ids = set(item for item in seria.data['ids'].split(',') if item and item.isdigit())
            if request.query_params.get('action', None) == 'cancel':
                cancel_followeeids = []
                with transaction.atomic():
                    for avid in ids:
                        deleted, _rows_count = models.SnsFollow.objects.filter(
                            user=request.user,
                            followee_id=avid
                        ).delete()
                        if deleted > 0:
                            models.UserStatistic.objects.filter(user=request.user).update(
                                followings_count=djangomodels.F('followings_count') - 1
                            )
                            models.UserStatistic.objects.filter(user_id=avid).update(
                                fans_count=djangomodels.F('fans_count') - 1
                            )
                            cancel_followeeids.append(avid)
                return Response(ok_data('取消关注投顾成功', data={'cancel_followeeids': cancel_followeeids}))
            else:
                followeeids = []
                with transaction.atomic():
                    for avid in ids:
                        # 投顾要存在且用户还没有关注
                        if models.UserInfo.objects.filter(
                            pk=avid
                        ).exists() and not models.SnsFollow.objects.filter(
                            user=request.user,
                            followee_id=avid
                        ).exists():

                            models.SnsFollow.objects.create(user=request.user, followee_id=avid)
                            followeeids.append(avid)
                return Response(ok_data('关注投顾成功', data={'followeeids': followeeids}))
        else:
            return fail_response_withseria(seria)
FollowInvestAdviser.mymeta = {
    'myurl': r'^user/follow_invest_adviser/$',
    'urlname': 'urlFollowInvestAdviser',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class SubscribePortfolio(GenericAPIView):
    """
    订阅牛组合(需要jwttoken).加上?action=cancel 表示取消订阅
    """
    class SubscribePortfolioSerializer(serializers.Serializer):
        ids = serializers.CharField(label='牛组合id', help_text='如果是多个话, 则 `1,2,3` 这样的格式')

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SubscribePortfolioSerializer

    def post(self, request, *args, **kwargs):
        seria = self.get_serializer(data=request.data)
        if seria.is_valid():
            ids = set(item for item in seria.data['ids'].split(',') if item and item.isdigit())
            if request.query_params.get('action', None) == 'cancel':
                cancelids = []
                with transaction.atomic():
                    for pid in ids:
                        deleted, _rows_count = models.SubscribePortfolio.objects.filter(
                            user=request.user,
                            portfolio_id=pid
                        ).delete()
                        if deleted > 0:
                            models.UserStatistic.objects.filter(
                                user_id=models.PortfolioBaseInfo.objects.only('owner_id').get(pk=pid).owner_id
                            ).update(
                                portfolios_bysubscribe_count=djangomodels.F('portfolios_bysubscribe_count') - 1
                            )
                            cancelids.append(pid)
                return Response(ok_data('取消订阅成功', data={"cancelids": cancelids}))
            else:
                subscribeids = []
                with transaction.atomic():
                    for pid in ids:
                        # 投顾要存在且用户还没有关注
                        if models.PortfolioBaseInfo.objects.filter(
                            pk=pid
                        ).exists() and not models.SubscribePortfolio.objects.filter(
                            user=request.user,
                            portfolio_id=pid
                        ).exists():

                            models.SubscribePortfolio.objects.create(user=request.user, portfolio_id=pid)
                            subscribeids.append(pid)
                return Response(ok_data('订阅牛组合成功', data={'subscribeids': subscribeids}))
        else:
            return fail_response_withseria(seria)
SubscribePortfolio.mymeta = {
    'myurl': r'^user/subscribe_portfolio/$',
    'urlname': 'urlSubscribePortfolio',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class SendSecurityCode(GenericAPIView):
    """
    给手机号发送验证码
    测试阶段, 验证码统一为: 1234
    """
    class SendSecurityCodeSerializer(serializers.Serializer):
        mobile = serializers.CharField(max_length=20)

    permission_classes = (permissions.AllowAny,)
    serializer_class = SendSecurityCodeSerializer

    def post(self, request, *args, **kwargs):
        seria = self.get_serializer(request.data)
        mobile = seria.data['mobile']
        # security_code = utils.get_random_verifycode(4)
        security_code = '1234'  # fixme  这里只是用于测试
        cache.set(securitycode_key(mobile), security_code, 5*60)  # 5分钟有效
        return Response(ok_data(msg='已发送验证码,5分钟有效'))

SendSecurityCode.mymeta = {
    'myurl': r'^send_securitycode/$',
    'urlname': 'urlSendSecurityCode',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class UserRegisterReadme(GenericAPIView):
    """
    用户注册协议
    """
    permission_classes = (permissions.AllowAny,)
    renderer_classes = (renderers.TemplateHTMLRenderer,)

    def get(self, request, *args, **kwargs):
        return Response(template_name='tg/user_register_readme.html')


UserRegisterReadme.mymeta = {
    'myurl': r'^user_register_readme/$',
    'urlname': 'UrlUserRegisterReadme',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class UserRegister(GenericAPIView):
    """
    用户注册
    """
    class UserRegisterSerializer(serializers.Serializer):
        mobile = serializers.CharField()
        security_code = serializers.CharField()
        nick_name = serializers.CharField(required=False)
        password = serializers.CharField()
        avatar = serializers.ImageField(required=False)

        def validate_mobile(self, value):
            if models.UserInfo.objects.filter(mobile=value).exists():
                raise exceptions.ValidationError('手机号已被注册')
            return value

        def validate(self, attrs):
            if attrs['security_code'].strip() != cache.get(securitycode_key(attrs['mobile'])):
                raise exceptions.ValidationError('验证码不正确')
            return attrs

        def create(self, validated_data):
            mobile = validated_data['mobile']
            user = models.UserInfo(
                user_class=models.UserInfo.T_INVESTOR,
                mobile=mobile,
            )
            if validated_data.get('nick_name', None):
                user.nick_name = validated_data['nick_name']
            if validated_data.get('avatar', None):
                user.avatar = validated_data['avatar']
            user.set_password(validated_data['password'])
            user.username = 'mob_' + mobile
            user.save()
            cache.delete(securitycode_key(mobile))
            return user

    permission_classes = (permissions.AllowAny,)
    serializer_class = UserRegisterSerializer

    def post(self, request, *args, **kwargs):
        seria = self.get_serializer(data=request.data)
        if seria.is_valid():
            user = seria.save()
            data = tg_serializers.CurUserInfoSerializer(user, context=self.get_serializer_context()).data
            return Response(ok_data(msg='新用户注册成功', data=data))
        else:
            return fail_response_withseria(seria)
UserRegister.mymeta = {
    'myurl': r'^user_register/$',
    'urlname': 'urlUserRegister',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1


class ForgetPasswd(GenericAPIView):
    """
    忘记密码
    """
    class ForgetPasswdSerializer(serializers.Serializer):
        mobile = serializers.CharField()
        security_code = serializers.CharField()
        password = serializers.CharField()

        def validate_mobile(self, value):
            rs = models.UserInfo.objects.filter(mobile=value)[:1]
            if rs:
                self.user = rs[0]
                return value
            else:
                raise exceptions.ValidationError('不存在该手机号:{}'.format(value))

        def validate(self, attrs):
            if cache.get(securitycode_key(attrs['mobile'])) != attrs['security_code'].strip():
                raise exceptions.ValidationError('校验码不对')
            return attrs

        def create(self, validated_data):
            self.user.set_password(validated_data['password'])
            self.user.save(force_update=True, update_fields=('password',))
            cache.delete(securitycode_key(validated_data['mobile']))
            return self.user

    permission_classes = (permissions.AllowAny,)
    serializer_class = ForgetPasswdSerializer

    def post(self, request, *args, **kwargs):
        seria = self.get_serializer(data=request.data)
        if seria.is_valid():
            seria.save()
            return Response(ok_data(msg='修改密码成功'))
        else:
            return fail_response_withseria(seria)

ForgetPasswd.mymeta = {
    'myurl': r'^forget_passwd/$',
    'urlname': 'urlForgetPasswd',
    'urlkwargs': {},
    'seq': apiseq
}
apiseq += 1

