# Generated by Django 2.2.16 on 2021-02-08 19:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hqwebapp', '0007_accesslog_nullable_ip'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserAgent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(db_index=True, max_length=255)),
            ],
        ),
        migrations.AlterField(
            model_name='useraccesslog',
            name='user_agent',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT,
                to='hqwebapp.UserAgent'),
        ),
    ]
