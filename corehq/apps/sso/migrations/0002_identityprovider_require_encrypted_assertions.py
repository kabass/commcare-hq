# Generated by Django 2.2.16 on 2021-04-01 18:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sso', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='identityprovider',
            name='require_encrypted_assertions',
            field=models.BooleanField(default=False),
        ),
    ]
