# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-10 04:37
from __future__ import unicode_literals

from django.db import migrations, models
import tg.models


class Migration(migrations.Migration):

    dependencies = [
        ('tg', '0004_add_col2portfolio'),
    ]

    operations = [
        migrations.CreateModel(
            name='News',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='\u6807\u9898')),
                ('topics', models.CharField(max_length=512, verbose_name='\u4e3b\u9898')),
                ('digest', models.CharField(blank=True, max_length=400, verbose_name='\u6458\u8981')),
                ('content', models.TextField(blank=True, verbose_name='\u5185\u5bb9')),
                ('pub_daytime', models.DateTimeField(blank=True, null=True, verbose_name='\u53d1\u5e03\u65f6\u95f4')),
                ('sub_picture', models.ImageField(blank=True, max_length=320, null=True, upload_to=tg.models.investviewpoint_subpic_uploadto, verbose_name='\u914d\u56fe')),
            ],
            options={
                'db_table': 'data_news',
                'verbose_name': '\u65b0\u95fb',
                'verbose_name_plural': '\u65b0\u95fb',
            },
        ),
    ]
