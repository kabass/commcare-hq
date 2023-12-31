# Generated by Django 3.2.18 on 2023-05-29 16:14

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_dictionary', '0012_populate_case_property_groups'),
    ]

    operations = [
        migrations.AddField(
            model_name='casepropertygroup',
            name='deprecated',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='caseproperty',
            name='description',
            field=models.TextField(blank=True, default='', validators=[django.core.validators.MaxLengthValidator(255, message='Property description should be less than 255 characters')]),
        ),
        migrations.AlterField(
            model_name='casepropertygroup',
            name='description',
            field=models.TextField(blank=True, default='', validators=[django.core.validators.MaxLengthValidator(255, message='Group description should be less than 255 characters')]),
        ),
        migrations.AlterUniqueTogether(
            name='casepropertygroup',
            unique_together={('case_type', 'name')},
        ),
    ]
