# Generated by Django 2.2.24 on 2021-07-23 19:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('linked_domain', '0018_auto_20210806_1526'),
    ]

    operations = [
        migrations.AlterField(
            model_name='domainlink',
            name='remote_base_url',
            field=models.CharField(blank=True,
                                   help_text='should be the full link without the trailing /. '
                                             'Example: https://www.commcarehq.org',
                                   max_length=255,
                                   null=True),
        ),
    ]
