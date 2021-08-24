# Generated by Django 2.2.24 on 2021-08-25 12:57

import django.contrib.postgres.fields.jsonb
from django.db import migrations

import corehq.util.validation
from corehq.apps.registry.schema import REGISTRY_JSON_SCHEMA


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataregistry',
            name='schema',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, validators=[corehq.util.validation.JSONSchemaValidator(REGISTRY_JSON_SCHEMA)]),
        ),
    ]
