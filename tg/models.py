# coding=utf-8
from __future__ import unicode_literals

import logging
import uuid

import arrow
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import UserManager, PermissionsMixin
from django.core import validators
from django.core.mail import send_mail
from django.db import models, transaction
from django.utils.encoding import python_2_unicode_compatible
from django.utils import timezone

logger = logging.getLogger('wh')

USER_COL_NAME = 'uid'
OWNER_USER_COL_NAME = 'own_uid'  # 所有的者 id


def uuid_hex_str():
    return uuid.uuid4().get_hex()


@python_2_unicode_compatible
class SecModel(models.Model):
    """
    证券信息
    """
    sec_type = models.IntegerField('类型')
    sec_id = models.CharField('代码', max_length=12, db_index=True)
    sec_name = models.CharField('名称', max_length=32)
    exchange = models.CharField('市场代码', max_length=8)
    symbol = models.CharField('证券标识(市场.代码)', max_length=40, db_index=True)
    is_active = models.BooleanField('是否有效', default=True)

    class Meta:
        db_table = 'data_sec_model'
        verbose_name = '证券信息'
        verbose_name_plural = '证券信息'

    def __str__(self):
        return "sec_id={self.sec_id} sec_name={self.sec_name} exchange={self.exchange}".format(self=self)


def userinfo_avatar_uploadto(instance, filename):
    return 'useravatar/{}/{}.{}'.format(arrow.get().format('YYYY/MM/DD'), uuid_hex_str(), filename.split('.')[::-1][0])


class UserInfoQuerySet(models.QuerySet):
    def investor(self):
        """
        普通股民
        """
        return self.filter(user_class=UserInfo.T_INVESTOR)

    def adviser(self):
        """
        投顾
        """
        return self.filter(user_class=UserInfo.T_ADVISER)


class UserInfoManager(UserManager):
    def get_queryset(self):
        return UserInfoQuerySet(self.model, self._db)

    def investor(self):
        """
        普通股民
        """
        return self.get_queryset().investor()

    def adviser(self):
        """
        投顾
        """
        return self.get_queryset().adviser()


@python_2_unicode_compatible
class UserInfo(AbstractBaseUser, PermissionsMixin):
    """
    用户信息表

    关于 reverse relation 信息
    面向投顾的
    portfolio_base_infos   投资组合信息
    viewpoints             投资观点
    recommend_securitys    推荐的股票
    sign_investors         签约的普通投资者

    investadviserinfo      投顾信息
    investadviserkpi       投顾kpi指标值 (衡量投顾)

    面向普通投资者的
    subscribe_portfolios   订阅的组合
    sign_advisers          签约的投顾
    followings             用户关注的人
    followers              用户的粉丝. (也就是用户被关注)

    userstatistic          用户的统计信息

    """
    T_INVESTOR, T_ADVISER, T_SYSTEM = (1, 2, 3)
    USER_CLASSES = (
        (T_INVESTOR, '普通股民'),
        (T_ADVISER, '投顾'),
        (T_SYSTEM, '系统用户'),
    )
    G_MAN, G_WOMAN, G_SECRET = (1, 2, 3)
    GENDER_TYPE = (
        (G_MAN, '男'),
        (G_WOMAN, '女'),
        (G_SECRET, '保密'),
    )

    user_class = models.SmallIntegerField('用户类别', choices=USER_CLASSES, blank=True, null=True)
    username = models.CharField(
        '用户名', max_length=64, unique=True, help_text='必填。不多于64个字符。只能用字母、数字和字符 @/./+/-/_',
        validators=[
            validators.RegexValidator(r'^[\w.@+-]+$', '请输入合法用户名。只能包含字母，数字和@/./+/-/_ 字符'),
        ],
        error_messages={
            'unique': "已存在一位使用该名字的用户",
        },
    )
    first_name = models.CharField('名字', max_length=30, blank=True)
    last_name = models.CharField('姓氏', max_length=30, blank=True)
    email = models.EmailField('电子邮件地址', blank=True, db_index=True)
    is_staff = models.BooleanField('职员状态', default=False, help_text='指明用户是否可以登录到这个管理站点', )
    is_active = models.BooleanField('有效', default=True, help_text='指明用户是否被认为活跃的。以反选代替删除帐号', )
    date_joined = models.DateTimeField('加入日期', default=timezone.now)

    mobile = models.CharField('手机号码', max_length=16, blank=True, db_index=True, )
    nick_name = models.CharField('昵称', max_length=64, blank=True)
    avatar = models.ImageField('头像地址', upload_to=userinfo_avatar_uploadto, max_length=240, blank=True, null=True)
    misc = models.TextField('杂项', blank=True)
    gender = models.SmallIntegerField('性别', choices=GENDER_TYPE, default=G_SECRET)

    objects = UserInfoManager()
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        swappable = 'AUTH_USER_MODEL'
        db_table = 'data_user_info'
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return self.username

    @transaction.atomic
    def save(self, *args, **kwargs):
        return super(UserInfo, self).save(*args, **kwargs)

    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        send_mail(subject, message, from_email, [self.email], **kwargs)

    @classmethod
    def find_by_email_or_mobile(cls, q):
        """
        按 email 或 mobile 查找用户. 如果没有找到则返回 None, 找到则返回第一个匹配的
        """
        qs = cls.objects.filter(models.Q(email=q) | models.Q(mobile=q))
        return qs[0] if qs else None


@python_2_unicode_compatible
class InvestAdviserInfo(models.Model):
    """
    投顾信息
    """
    user = models.OneToOneField(UserInfo, primary_key=True, limit_choices_to={'user_class': UserInfo.T_ADVISER})

    title = models.CharField('职称', max_length=60, null=True, blank=True)
    title_certificate = models.CharField('资质证书号', max_length=60, blank=True)
    experience = models.CharField('从业经验', max_length=2048, blank=True)
    good_at = models.CharField('擅长领域', max_length=2048, blank=True)

    class Meta:
        db_table = 'data_invest_adv_info'
        verbose_name = '投顾信息'
        verbose_name_plural = '投顾信息'

    def __str__(self):
        return "user_id={}".format(self.user_id)


@python_2_unicode_compatible
class InvestAdviserKpi(models.Model):
    """
    投顾kpi指标值 (衡量投顾)
    """
    user = models.OneToOneField(UserInfo, primary_key=True, limit_choices_to={'user_class': UserInfo.T_ADVISER})

    success_ratio = models.DecimalField('荐股成功率', max_digits=12, decimal_places=3)
    accumulate_profit_ratio = models.DecimalField('累计收益率', max_digits=12, decimal_places=3)

    class Meta:
        db_table = 'data_invest_adv_kpi'
        verbose_name = '投顾kpi指标值'
        verbose_name_plural = '投顾kpi指标值'

    def __str__(self):
        return "InvestAdviserKpi userid=".format(self.user_id)


@python_2_unicode_compatible
class UserStatistic(models.Model):
    """
    用户的统计信息
    """
    user = models.OneToOneField(UserInfo, primary_key=True)

    fans_count = models.PositiveIntegerField('粉丝数', default=0)
    followings_count = models.PositiveIntegerField('关注数', default=0)

    # 针对投顾
    sign_contract_count = models.PositiveIntegerField('签约股民数', default=0)
    recommend_secs_count = models.PositiveIntegerField('推荐股票数', default=0)
    portfolios_count = models.PositiveIntegerField('投资组合数', default=0)
    portfolios_bysubscribe_count = models.PositiveIntegerField('投资组合被订阅次数', default=0)
    viewpoints_count = models.PositiveIntegerField('投资观点数', default=0)

    class Meta:
        db_table = 'data_user_stat'
        verbose_name = '用户统计信息'
        verbose_name_plural = '用户统计信息'

    def __str__(self):
        return "user_id={}".format(self.user_id)


class SnsFollowManager(models.Manager):
    @transaction.atomic
    def create(self, **kwargs):
        obj = super(SnsFollowManager, self).create(**kwargs)
        UserStatistic.objects.filter(user=obj.user).update(followings_count=models.F('followings_count') + 1)
        UserStatistic.objects.filter(user=obj.followee).update(fans_count=models.F('fans_count') + 1)
        return obj


@python_2_unicode_compatible
class SnsFollow(models.Model):
    """
    用户之间的关注
    """
    objects = SnsFollowManager()

    user = models.ForeignKey(UserInfo, related_name="followings")  # 用户关注的人
    followee = models.ForeignKey(UserInfo, related_name="followers")  # 用户的粉丝. (也就是用户被关注)
    ctime = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "sns follow : {0} -> {1}".format(self.user, self.followee)

    class Meta:
        db_table = 'data_sns_follow'
        unique_together = (("user", "followee"),)
        verbose_name = '用户间关注'
        verbose_name_plural = '用户间关注'


class PortfolioBaseInfoManager(models.Manager):
    @transaction.atomic
    def create(self, **kwargs):
        obj = super(PortfolioBaseInfoManager, self).create(**kwargs)  # type: PortfolioBaseInfo
        UserStatistic.objects.filter(user=obj.owner).update(portfolios_count=models.F('portfolios_count') + 1)


@python_2_unicode_compatible
class PortfolioBaseInfo(models.Model):
    """
    投资组合基本信息

    关于 reverse relation 信息
    subscribe_investors    订阅的普通投资者
    """
    objects = PortfolioBaseInfoManager()

    owner = models.ForeignKey(UserInfo, db_column=OWNER_USER_COL_NAME,
                              related_name='portfolio_base_infos',  # 用户的投资组合信息
                              limit_choices_to={'user_class': UserInfo.T_ADVISER})

    uuid = models.CharField('来自于api创建的投组id', max_length=100, blank=True, unique=True)
    name = models.CharField('名称', max_length=100)
    topics = models.CharField('主题', max_length=100, blank=True)
    note = models.CharField('说明', max_length=200, blank=True)
    ctime = models.DateTimeField('创建时间', default=timezone.now)

    # 计算指标值
    curdate_ratio = models.DecimalField('当日收益率', max_digits=12, decimal_places=4, default=0)
    week_ratio = models.DecimalField('周收益率', max_digits=12, decimal_places=4, default=0)
    month_ratio = models.DecimalField('月收益率', max_digits=12, decimal_places=4, default=0)
    accumulate_ratio = models.DecimalField('累计收益率', max_digits=12, decimal_places=4, default=0)

    success_ratio = models.DecimalField('荐股成功率', max_digits=12, decimal_places=3, default=0)

    def __str__(self):
        return 'PortfolioBaseInfo, name={}, uuid={}'.format(self.name, self.uuid)

    class Meta:
        db_table = 'data_portfolio_baseinfo'
        verbose_name = '投资组合基本信息'
        verbose_name_plural = '投资组合基本信息'


def investviewpoint_subpic_uploadto(instance, filename):
    return "viewpoint/{}/{}.{}".format(arrow.get().format("YYYY/MM/DD"), uuid_hex_str(), filename.split('.')[::-1][0])


class InvestViewpointManager(models.Manager):
    @transaction.atomic
    def create(self, **kwargs):
        obj = super(InvestViewpointManager, self).create(**kwargs)  # type:InvestViewpoint
        UserStatistic.objects.filter(user=obj.owner).update(viewpoints_count=models.F('viewpoints_count') + 1)


@python_2_unicode_compatible
class InvestViewpoint(models.Model):
    """
    投资观点
    """
    objects = InvestViewpointManager()

    owner = models.ForeignKey(UserInfo, db_column=OWNER_USER_COL_NAME, related_name='viewpoints',  # 用户的投资观点
                              limit_choices_to={'user_class': UserInfo.T_ADVISER})

    title = models.CharField('标题', max_length=200)
    digest = models.CharField('摘要', max_length=400, blank=True)
    content = models.CharField('内容', max_length=1024 * 20, blank=True)
    pub_daytime = models.DateTimeField('发布时间', blank=True, null=True)
    sub_picture = models.ImageField('配图', upload_to=investviewpoint_subpic_uploadto, max_length=320,
                                    blank=True, null=True)

    def __str__(self):
        return 'InvestViewpoint, title={}'.format(self.title)

    class Meta:
        db_table = 'data_invest_viewpoint'
        verbose_name = '投资观点'
        verbose_name_plural = '投资观点'


@python_2_unicode_compatible
class News(models.Model):
    title = models.CharField('标题', max_length=200)
    topics = models.CharField('主题', max_length=512)
    digest = models.CharField('摘要', max_length=400, blank=True)
    content = models.TextField('内容', blank=True)
    pub_daytime = models.DateTimeField('发布时间', blank=True, null=True)
    sub_picture = models.ImageField('配图', upload_to=investviewpoint_subpic_uploadto, max_length=320,
                                    blank=True, null=True)

    def __str__(self):
        return 'News, title={}'.format(self.title)

    class Meta:
        db_table = 'data_news'
        verbose_name = '新闻'
        verbose_name_plural = '新闻'


class InvestRecommendSecurityManager(models.Manager):
    @transaction.atomic
    def create(self, **kwargs):
        obj = super(InvestRecommendSecurityManager, self).create(**kwargs)  # type: InvestRecommendSecurity
        UserStatistic.objects.filter(user=obj.owner).update(recommend_secs_count=models.F('recommend_secs_count') + 1)


@python_2_unicode_compatible
class InvestRecommendSecurity(models.Model):
    """
    投顾推荐股票
    """
    objects = InvestRecommendSecurityManager()

    owner = models.ForeignKey(UserInfo, db_column=OWNER_USER_COL_NAME,
                              related_name='recommend_securitys',   # 推荐的股票
                              limit_choices_to={'user_class': UserInfo.T_ADVISER})

    sec_idxid = models.CharField(
        '标识股票id', max_length=20,
        help_text='市场.股票代码. 如 SZSE.000001代表平安银行'
    )
    buy_daytime = models.DateTimeField('买入时间')
    buy_price = models.DecimalField('买入价格', max_digits=12, decimal_places=4)
    sell_daytime = models.DateTimeField('卖出时间', blank=True, null=True)
    sell_price = models.DecimalField('卖出价格', max_digits=12, decimal_places=4, blank=True, null=True)
    ctime = models.DateTimeField('创建时间', default=timezone.now)

    # 计算指标值
    curdate_ratio = models.DecimalField('当日收益率', max_digits=12, decimal_places=4, default=0)
    week_ratio = models.DecimalField('周收益率',  max_digits=12, decimal_places=4, default=0)
    month_ratio = models.DecimalField('月收益率',  max_digits=12, decimal_places=4, default=0)
    accumulate_ratio = models.DecimalField('累计收益率', max_digits=12, decimal_places=4, default=0)

    class Meta:
        db_table = 'data_invest_recommend_sec'
        verbose_name = '投顾推荐股票'
        verbose_name_plural = '投顾推荐股票'

    def __str__(self):
        return "owner_id={}, sec_idxid={}".format(self.owner_id, self.sec_idxid)


class SubscribePorfolioManager(models.Manager):
    @transaction.atomic
    def create(self, **kwargs):
        obj = super(SubscribePorfolioManager, self).create(**kwargs)   # type: SubscribePortfolio
        UserStatistic.objects.filter(user=obj.portfolio.owner).update(
            portfolios_bysubscribe_count=models.F('portfolios_bysubscribe_count') + 1
        )


@python_2_unicode_compatible
class SubscribePortfolio(models.Model):
    """
    用户订阅组合
    """
    objects = SubscribePorfolioManager()

    user = models.ForeignKey(
        UserInfo, verbose_name='订阅者', db_column=USER_COL_NAME,
        related_name='subscribe_portfolios',   # 订阅的组合
        on_delete=models.DO_NOTHING
    )
    portfolio = models.ForeignKey(
        PortfolioBaseInfo, verbose_name='投组',
        related_name='subscribe_investors',    # 订阅的客户
        on_delete=models.DO_NOTHING
    )
    ctime = models.DateTimeField('创建时间', default=timezone.now)
    note = models.CharField('备注说明', blank=True, max_length=300)

    class Meta:
        db_table = 'data_subscribe_portfolio'
        verbose_name = '用户订阅组合'
        verbose_name_plural = '用户订阅组合'
        unique_together = (("user", "portfolio"),)

    def __str__(self):
        return "user_id={} subscribe portfolio_id".format(self.user_id, self.portfolio_id)


class SignContractManager(models.Manager):
    @transaction.atomic
    def create(self, **kwargs):
        obj = super(SignContractManager, self).create(**kwargs)  # type: SignContract
        UserStatistic.objects.filter(user=obj.adviser).update(
            sign_contract_count = models.F('sign_contract_count') + 1
        )


@python_2_unicode_compatible
class SignContract(models.Model):
    """
    用户签约投顾
    """
    objects = SignContractManager()

    user = models.ForeignKey(
        UserInfo, verbose_name='用户', db_column=USER_COL_NAME,
        related_name='sign_advisers',  # 签约的投顾
        on_delete=models.DO_NOTHING
    )

    adviser = models.ForeignKey(
        UserInfo, verbose_name='投顾', db_column='adviser_id',
        related_name='sign_investors',  # 签约的客户
        on_delete=models.DO_NOTHING
    )
    ctime = models.DateTimeField('创建时间', default=timezone.now)
    note = models.CharField('备注说明', blank=True, max_length=300)

    class Meta:
        db_table = 'data_sign_contract'
        verbose_name = '用户签约投顾'
        verbose_name_plural = '用户签约投顾'

    def __str__(self):
        return "user_id={} sign contract to adviser_id={}".format(self.user_id, self.adviser_id)


def ad_picture_uploadto(instance, filename):
    return "ad/{}/{}.{}".format(arrow.get().format("YYYY/MM/DD"), uuid_hex_str(), filename.split('.')[::-1][0])


@python_2_unicode_compatible
class Ad(models.Model):
    """
    广告
    """
    picture = models.ImageField('题图', upload_to=ad_picture_uploadto)
    title = models.CharField('标题', blank=True, max_length=100)
    goto_url = models.CharField('跳转的url', blank=True, max_length=300)
    ctime = models.DateTimeField('创建时间', default=timezone.now)
    isvalid = models.BooleanField('是否有效', default=True)

    class Meta:
        db_table = 'data_ad'
        verbose_name = '广告'
        verbose_name_plural = '广告'

    def __str__(self):
        return "Ad id = {}".format(self.id)


@python_2_unicode_compatible
class ApplyAdviserJob(models.Model):
    """
    申请投顾工作信息
    """
    T_WAIT, T_PASS, T_REJECT = (1, 2, 3)
    STATUSSET = (
        (T_WAIT, '待审核'),
        (T_PASS, '通过'),
        (T_REJECT, '拒绝'),
    )

    real_name = models.CharField('真实姓名', max_length=40)
    phone = models.CharField('手机号', max_length=20)
    title_certificate = models.CharField('资质证书号', max_length=60)
    status = models.SmallIntegerField('状态', choices=STATUSSET, default=T_WAIT)

    class Meta:
        db_table = 'data_apply_adviser_job'
        verbose_name = '申请投顾工作信息'
        verbose_name_plural = '申请投顾工作信息'

    def __str__(self):
        return "ApplyAdviserJob id={}".format(self.id)
