from django.db import migrations

from corehq.form_processor.models import XFormInstance
from corehq.sql_db.operations import RawSQLMigration

migrator = RawSQLMigration(('corehq', 'sql_accessors', 'sql_templates'), {
    'FORM_STATE_DELETED': XFormInstance.DELETED
})


class Migration(migrations.Migration):

    dependencies = [
        ('sql_accessors', '0014_ledger_transactions'),
    ]

    operations = [
        migrator.get_migration('get_ledger_transactions_for_case.sql'),
    ]
