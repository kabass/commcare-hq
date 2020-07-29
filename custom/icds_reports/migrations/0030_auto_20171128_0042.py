# Generated by Django 1.11.7 on 2017-11-28 00:42
from corehq.sql_db.operations import RawSQLMigration
from django.db import migrations

from custom.icds_reports.const import SQL_TEMPLATES_ROOT

migrator = RawSQLMigration((SQL_TEMPLATES_ROOT,))


class Migration(migrations.Migration):

    dependencies = [
        ('icds_reports', '0029_add_add_and_dob_to_intermediate_tables'),
    ]

    operations = [
        migrator.get_migration('update_tables14.sql'),
    ]
