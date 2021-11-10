# Generated by Django 2.2.24 on 2021-07-23 20:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('enterprise', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='enterprisepermissions',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounting.BillingAccount',
                                    unique=True),
        ),
    ]
