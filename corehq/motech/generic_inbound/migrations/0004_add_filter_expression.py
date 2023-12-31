# Generated by Django 3.2.15 on 2022-09-28 13:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('userreports', '0019_ucrexpression_upstream_id'),
        ('generic_inbound', '0003_add_logging_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='configurableapi',
            name='filter_expression',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='api_filter', to='userreports.ucrexpression'),
        ),
        migrations.AlterField(
            model_name='configurableapi',
            name='transform_expression',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='api_expression', to='userreports.ucrexpression'),
        ),
    ]
