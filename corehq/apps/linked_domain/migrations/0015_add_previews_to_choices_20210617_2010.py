# Generated by Django 2.2.24 on 2021-06-17 20:10

from django.db import migrations, models

from corehq.apps.linked_domain.const import MODEL_PREVIEWS, MODEL_FLAGS
from corehq.apps.linked_domain.models import DomainLinkHistory
from corehq.util.django_migrations import skip_on_fresh_install


@skip_on_fresh_install
def _duplicate_toggle_events_into_preview_events(apps, schema_editor):
    all_toggle_events = DomainLinkHistory.objects.filter(model=MODEL_FLAGS)
    # iterate through events, copy into a new entry with model='previews'
    for toggle_event in all_toggle_events:
        toggle_event.pk = None
        toggle_event.model = MODEL_PREVIEWS
        toggle_event.save()


class Migration(migrations.Migration):

    dependencies = [
        ('linked_domain', '0014_auto_20210503_1758'),
    ]

    operations = [
        migrations.AlterField(
            model_name='domainlinkhistory',
            name='model',
            field=models.CharField(choices=[
                ('app', 'Application'),
                ('fixture', 'Lookup Table'),
                ('report', 'Report'),
                ('keyword', 'Keyword'),
                ('custom_user_data', 'Custom User Data Fields'),
                ('custom_product_data', 'Custom Product Data Fields'),
                ('custom_location_data', 'Custom Location Data Fields'),
                ('roles', 'User Roles'),
                ('previews', 'Feature Previews'),
                ('case_search_data', 'Case Search Settings'),
                ('data_dictionary', 'Data Dictionary'),
                ('dialer_settings', 'Dialer Settings'),
                ('otp_settings', 'OTP Pass-through Settings'),
                ('hmac_callout_settings', 'Signed Callout'),
                ('toggles', 'Feature Flags')
            ], max_length=128),
        ),
        migrations.RunPython(_duplicate_toggle_events_into_preview_events),
    ]
