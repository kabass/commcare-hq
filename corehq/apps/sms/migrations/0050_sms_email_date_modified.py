# Generated by Django 2.2.24 on 2021-06-29 13:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sms', '0049_auto_enable_turnio_ff'),
    ]

    operations = [
        migrations.AddField(
            model_name='email',
            name='date_modified',
            field=models.DateTimeField(auto_now=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='sms',
            name='date_modified',
            field=models.DateTimeField(auto_now=True, db_index=True, null=True),
        ),
    ]
