# Generated by Django 2.2.20 on 2021-06-08 21:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mobile_auth', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='SQLMobileAuthKeyRecord',
        ),
    ]
