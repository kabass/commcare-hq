# Generated by Django 2.2.24 on 2021-10-11 13:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0005_auto_20210923_1036'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registryauditlog',
            name='action',
            field=models.CharField(choices=[
                ('activated', 'Registry Activated'),
                ('deactivated', 'Registry De-activated'),
                ('invitation_removed', 'Invitation Revoked'),
                ('schema', 'Schema Changed'),
                ('invitation_accepted', 'Invitation Accepted'),
                ('invitation_rejected', 'Invitation Rejected'),
                ('grant_added', 'Grant created'),
                ('grant_removed', 'Grant removed'),
                ('data_accessed', 'Data Accessed'),
                ('invitation_added', 'Invitation Added')
            ], max_length=32),
        ),
    ]
