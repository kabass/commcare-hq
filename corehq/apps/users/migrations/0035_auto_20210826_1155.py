# Generated by Django 2.2.24 on 2021-08-26 11:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0034_auto_20210813_1121'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='userhistory',
            name='users_userh_domain_4e500e_idx',
        ),
        migrations.RenameField(
            model_name='userhistory',
            old_name='domain',
            new_name='by_domain',
        ),
        migrations.AddField(
            model_name='userhistory',
            name='for_domain',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddIndex(
            model_name='userhistory',
            index=models.Index(fields=['by_domain'], name='users_userh_by_doma_f0f83d_idx'),
        ),
        migrations.AddIndex(
            model_name='userhistory',
            index=models.Index(fields=['for_domain'], name='users_userh_for_dom_1a4a54_idx'),
        ),
    ]
