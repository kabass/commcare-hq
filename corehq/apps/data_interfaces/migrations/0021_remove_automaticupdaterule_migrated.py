# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-09-14 12:21
from __future__ import unicode_literals
from __future__ import absolute_import
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_interfaces', '0020_make_migrated_nullable'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='automaticupdaterule',
            name='migrated',
        ),
    ]
