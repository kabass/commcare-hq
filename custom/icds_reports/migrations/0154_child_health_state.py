# -*- coding: utf-8 -*-
# Generated by Django 1.11.26 on 2019-12-04 05:51
from __future__ import unicode_literals

from corehq.sql_db.operations import RawSQLMigration
from django.db import migrations

from custom.icds_reports.const import SQL_TEMPLATES_ROOT

migrator = RawSQLMigration((SQL_TEMPLATES_ROOT, 'database_views'))


class Migration(migrations.Migration):

    dependencies = [
        ('icds_reports', '0153_daily_attendance_state'),
    ]

    operations = [
        migrations.RunSQL("ALTER TABLE child_health_monthly ADD COLUMN state_id text"),
    ]
