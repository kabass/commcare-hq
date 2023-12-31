# Generated by Django 3.2.15 on 2022-11-15 14:11

from django.db import migrations, models


TABLE_NAME = 'sms_messagingsubevent'
INDEX_NAME = 'sms_messagingsubevent_domain_date_last_activity_id_f8451fac_idx'
COLUMNS = ['domain', 'date_last_activity', 'id']

CREATE_INDEX_SQL = "CREATE INDEX CONCURRENTLY IF NOT EXISTS {} ON {} ({})".format(
    INDEX_NAME, TABLE_NAME, ','.join(COLUMNS))
DROP_INDEX_SQL = "DROP INDEX CONCURRENTLY IF EXISTS {}".format(INDEX_NAME)



class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('sms', '0054_messagingsubevent_domain'),
    ]

    operations = [
        # replace single field index with combined index
        migrations.AlterField(
            model_name='messagingsubevent',
            name='date_last_activity',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.RunSQL(
            sql=CREATE_INDEX_SQL,
            reverse_sql=DROP_INDEX_SQL,
            state_operations=[
                migrations.AlterIndexTogether(
                    name='messagingsubevent',
                    index_together={('domain', 'date_last_activity', 'id')},
                ),
            ]
        )
    ]
