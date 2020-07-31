# -*- coding: utf-8 -*-
# Generated by Django 1.11.22 on 2019-10-17
from __future__ import unicode_literals

from corehq.sql_db.operations import RawSQLMigration
from django.db import migrations

from custom.icds_reports.const import SQL_TEMPLATES_ROOT

migrator = RawSQLMigration((SQL_TEMPLATES_ROOT, 'database_views'))


class Migration(migrations.Migration):

    dependencies = [
        ('icds_reports', '0140_auto_20191024_1048'),
    ]

    operations = [
        migrations.RunSQL("ALTER table agg_awc_daily DROP COLUMN total_eligible_pse"),
    ]
