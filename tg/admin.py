# coding=utf-8
from __future__ import (unicode_literals, absolute_import, print_function)
import itertools

from django.contrib import admin
from django.contrib.auth import admin as authadmin
from django.db import connection

from . import models, forms


def get_user_username(obj):
    return obj.user.username
get_user_username.short_description = '用户名'


def get_user_nickname(obj):
    return obj.user.nick_name
get_user_nickname.short_description = '昵称'


def get_owner_username(obj):
    return obj.owner.username
get_owner_username.short_description = '所有者用户名'


def get_owner_nickname(obj):
    return obj.owner.nick_name
get_owner_nickname.short_description = '所有者昵称'


@admin.register(models.SecModel)
class SecModelAdmin(admin.ModelAdmin):
    pass


@admin.register(models.UserInfo)
class UserInfoAdmin(authadmin.UserAdmin):
    list_display = ('id', 'user_class', 'username', 'nick_name', 'email', 'mobile', 'date_joined',)
    search_fields = ('username', 'email', 'mobile', 'nick_name')
    search_placeholder = '用户名 / 昵称 / email / 手机'
    list_filter = ('user_class', 'is_staff', 'is_active', 'groups')
    filter_horizontal = ('groups', 'user_permissions',)

    form = forms.UserChangeForm
    add_form = forms.UserCreationForm

    fieldsets = (
        ('基本信息', {
            'fields': ('username', 'password', 'email', 'mobile'),
        }),
        ('用户类型及状态', {
            'classes': ('grp-collapse grp-open',),
            'fields': ('user_class', 'is_staff', 'is_active'),
        }),
        ('扩展信息', {
            'classes': ('grp-collapse grp-closed',),
            'fields': ('avatar', 'nick_name', 'first_name', 'last_name', ),
        })
    )
    superuser_fieldsets = fieldsets + (
        ('权限', {
            'classes': ('grp-collapse grp-closed',),
            'fields': ('groups', 'user_permissions')
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        else:
            if request.user.is_superuser:
                return self.superuser_fieldsets
            else:
                return self.fieldsets

    def get_queryset(self, request):
        queryset = super(UserInfoAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            pass
        elif request.user.is_staff:
            queryset = queryset.filter(is_staff=False, is_superuser=False)
        return queryset


@admin.register(models.InvestAdviserInfo)
class InvestAdviserInfoAdmin(admin.ModelAdmin):
    list_display = (get_user_username, get_user_nickname, 'title', 'title_certificate')
    search_fields = ('user__username', 'user__nick_name', 'title', 'title_certificate')
    search_placeholder = '用户名 / 昵称 / 职称 / 从业资格证书号'


@admin.register(models.InvestAdviserKpi)
class InvestAdviserKpiAdmin(admin.ModelAdmin):
    pass


@admin.register(models.UserStatistic)
class UserStatisticAdmin(admin.ModelAdmin):
    pass


@admin.register(models.SnsFollow)
class SnsFollowAdmin(admin.ModelAdmin):
    pass


@admin.register(models.PortfolioBaseInfo)
class PortfolioBaseInfoAdmin(admin.ModelAdmin):
    pass


@admin.register(models.InvestViewpoint)
class InvestViewpointAdmin(admin.ModelAdmin):
    pass


@admin.register(models.News)
class NewsAdmin(admin.ModelAdmin):
    pass


class InvestAdviserListFilter(admin.SimpleListFilter):
    """
    投顾筛选查询器
    """
    title = '投顾'
    parameter_name = 'InvestAdviser'

    def lookups(self, request, model_admin):
        sql = '''
SELECT DISTINCT
  ui.id,
  ui.username
FROM data_invest_recommend_sec AS recsec INNER JOIN data_user_info ui ON recsec.own_uid = ui.id
        '''
        with connection.cursor() as cursor:
            cursor.execute(sql)
            user_qs = cursor.fetchmany(40)
        return itertools.imap(lambda x, y: y, itertools.repeat(1, 40), user_qs)

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(owner__id=self.value())
        else:
            return queryset


@admin.register(models.InvestRecommendSecurity)
class InvestRecommendSecurityAdmin(admin.ModelAdmin):
    list_display = (
        get_owner_username, get_owner_nickname, 'sec_idxid', 'buy_daytime', 'buy_price', 'sell_daytime', 'sell_price',
        'curdate_ratio', 'week_ratio', 'month_ratio', 'accumulate_ratio', 'ctime'
    )
    ordering = ('-ctime', )
    list_filter = (InvestAdviserListFilter, )


@admin.register(models.SubscribePortfolio)
class SubscribePortfolioAdmin(admin.ModelAdmin):
    pass


@admin.register(models.SignContract)
class SignContractAdmin(admin.ModelAdmin):
    pass


@admin.register(models.Ad)
class AdAdmin(admin.ModelAdmin):
    pass


@admin.register(models.ApplyAdviserJob)
class ApplyAdviserJobAdmin(admin.ModelAdmin):
    pass
