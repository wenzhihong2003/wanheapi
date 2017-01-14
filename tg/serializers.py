# coding=utf-8
from __future__ import (unicode_literals, absolute_import, print_function)

import bleach
from rest_framework import serializers, status
from rest_framework.reverse import reverse
from rest_framework.exceptions import APIException

from . import models


class CurUserInfoSerializer(serializers.ModelSerializer):
    """
    当前用户信息
    """
    gender_cn = serializers.CharField(source='get_gender_display', read_only=True)

    class Meta:
        model = models.UserInfo
        fields = ('id', 'nick_name', 'username', 'mobile', 'avatar', 'gender', 'gender_cn')


class InvestAdviserBaseInfoSerializer(serializers.ModelSerializer):
    """
    投顾基本信息
    """
    id = serializers.IntegerField(source='user.id')
    avatar = serializers.ImageField(source='user.avatar')
    name = serializers.CharField(source='user.nick_name')
    success_ratio = serializers.SerializerMethodField()
    accumulate_profit_ratio = serializers.SerializerMethodField()
    fans = serializers.IntegerField(source='user.userstatistic.fans_count')
    is_follow = serializers.SerializerMethodField()
    is_sign_contract = serializers.SerializerMethodField()

    class Meta:
        model = models.InvestAdviserInfo
        fields = (
            'id', 'title', 'title_certificate',
            'avatar', 'name', 'success_ratio', 'accumulate_profit_ratio',
            'fans', 'is_follow', 'is_sign_contract',
        )

    def get_success_ratio(self, obj):
        return obj.user.investadviserkpi.success_ratio

    def get_accumulate_profit_ratio(self, obj):
        return obj.user.investadviserkpi.accumulate_profit_ratio

    def get_is_follow(self, obj):
        cur_user = self.context['request'].user   # type: models.UserInfo
        if getattr(self, 'follows', None) is None:
            if cur_user.is_anonymous():
                self.followings = set()
            else:
                self.followings = set(cur_user.followings.values_list('followee_id', flat=True))
        return obj.user_id in self.followings

    def get_is_sign_contract(self, obj):
        cur_user = self.context['request'].user  # type: models.UserInfo
        if getattr(self, 'sign_advisers', None) is None:
            if cur_user.is_anonymous():
                self.sign_advisers = set()
            else:
                self.sign_advisers = cur_user.sign_advisers.values_list('adviser_id', flat=True)
        return obj.user_id in self.sign_advisers


class InvestAdviserShortInfoSerializer(serializers.Serializer):
    """
    投顾简要信息. 从UserInfo信息开始导向
    """
    id = serializers.IntegerField()
    avatar = serializers.ImageField()
    name = serializers.CharField(source='nick_name')
    title = serializers.CharField(source='investadviserinfo.title')


class PortfolioBaseinfoSerializer(serializers.ModelSerializer):
    accumulate_profit_ratio = serializers.SerializerMethodField()
    invest_adviser = InvestAdviserShortInfoSerializer(source='owner')
    hold = serializers.SerializerMethodField()
    is_subscribe = serializers.SerializerMethodField()

    class Meta:
        model = models.PortfolioBaseInfo
        fields = ('id', 'uuid', 'name', 'accumulate_profit_ratio', 'topics', 'note', 'invest_adviser',
                  'success_ratio', 'hold', 'is_subscribe')

    def get_fields(self):
        fields = super(PortfolioBaseinfoSerializer, self).get_fields()
        if 'adviser_self' in self.context:  # 如果是投顾自身的话, 则不要序列化投顾信息
            fields.pop('invest_adviser')
        return fields

    def get_hold(self, obj):
        #  todo 这里先弄个0
        return 0

    def get_is_subscribe(self, obj):
        cur_user = self.context['request'].user  # type: models.UserInfo
        if getattr(self, 'subscribe_portfolios', None) is None:
            if cur_user.is_anonymous():
                self.subscribe_portfolios = set()
            else:
                self.subscribe_portfolios = cur_user.subscribe_portfolios.values_list('portfolio_id', flat=True)
        return obj.id in self.subscribe_portfolios

    def get_accumulate_profit_ratio(self, obj):
        return obj.accumulate_ratio


class RecommendSecuritySerializer(serializers.ModelSerializer):
    invest_adviser = InvestAdviserShortInfoSerializer(source='owner')

    def get_fields(self):
        fields = super(RecommendSecuritySerializer, self).get_fields()
        if 'adviser_self' in self.context:  # 如果是投顾自身的话, 则不要序列化投顾信息
            fields.pop('invest_adviser')
        return fields

    class Meta:
        model = models.InvestRecommendSecurity
        fields = ('id', 'sec_idxid', 'buy_daytime', 'buy_price', 'sell_daytime', 'sell_price', 'invest_adviser')


class InvestViewpointSerializer(serializers.ModelSerializer):
    invest_adviser = InvestAdviserShortInfoSerializer(source='owner')
    content = serializers.SerializerMethodField()
    html5 = serializers.SerializerMethodField()

    def get_fields(self):
        fields = super(InvestViewpointSerializer, self).get_fields()
        if 'adviser_self' in self.context: # 如果是投顾自身的话, 则不要序列化投顾信息
            fields.pop('invest_adviser')
        return fields

    def get_content(self, obj):
        return bleach.clean(obj.content, strip=True)

    def get_html5(self, obj):
        return reverse('UrlInvestViewpointInfo', kwargs={'pk': obj.id}, request=self.context['request'])

    class Meta:
        model = models.InvestViewpoint
        fields = (
            'id', 'title', 'digest', 'content', 'pub_daytime', 'sub_picture',
            'invest_adviser', 'html5'
        )
