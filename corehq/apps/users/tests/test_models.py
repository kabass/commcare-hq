from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from corehq.apps.users.models import (
    CommCareUser,
    CouchUser,
    Invitation,
    WebUser,
    DeviceAppMeta,
)

from corehq.apps.domain.models import Domain


class CouchUserTest(SimpleTestCase):

    def test_web_user_flag(self):
        self.assertTrue(WebUser().is_web_user())
        self.assertTrue(CouchUser.wrap(WebUser().to_json()).is_web_user())
        self.assertFalse(CommCareUser().is_web_user())
        self.assertFalse(CouchUser.wrap(CommCareUser().to_json()).is_web_user())
        with self.assertRaises(NotImplementedError):
            CouchUser().is_web_user()

    def test_commcare_user_flag(self):
        self.assertFalse(WebUser().is_commcare_user())
        self.assertFalse(CouchUser.wrap(WebUser().to_json()).is_commcare_user())
        self.assertTrue(CommCareUser().is_commcare_user())
        self.assertTrue(CouchUser.wrap(CommCareUser().to_json()).is_commcare_user())
        with self.assertRaises(NotImplementedError):
            CouchUser().is_commcare_user()


class InvitationTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super(InvitationTest, cls).setUpClass()
        cls.invitations = [
            Invitation(domain='domain_1', email='email1@email.com', invited_by='friend@email.com',
                       invited_on=datetime.utcnow()),
            Invitation(domain='domain_1', email='email1@email.com', invited_by='friend@email.com',
                       invited_on=datetime.utcnow(), is_accepted=True),
            Invitation(domain='domain_1', email='email2@email.com', invited_by='friend@email.com',
                       invited_on=datetime.utcnow(), is_accepted=True),
            Invitation(domain='domain_2', email='email3@email.com', invited_by='friend@email.com',
                       invited_on=datetime.utcnow()),
        ]
        for inv in cls.invitations:
            inv.save()

    def test_by_domain(self):
        self.assertEqual(len(Invitation.by_domain('domain_1')), 1)
        self.assertEqual(len(Invitation.by_domain('domain_1', is_accepted=True)), 2)
        self.assertEqual(len(Invitation.by_domain('domain_2')), 1)
        self.assertEqual(len(Invitation.by_domain('domain_3')), 0)

    def test_by_email(self):
        self.assertEqual(len(Invitation.by_email('email1@email.com')), 1)
        self.assertEqual(len(Invitation.by_email('email3@email.com')), 1)
        self.assertEqual(len(Invitation.by_email('email4@email.com')), 0)

    @classmethod
    def tearDownClass(cls):
        for inv in cls.invitations:
            inv.delete()
        super(InvitationTest, cls).tearDownClass()


class User_MessagingDomain_Tests(SimpleTestCase):
    def test_web_user_with_no_messaging_domain_returns_false(self):
        user = WebUser(domains=['domain_no_messaging_1', 'domain_no_messaging_2'])
        self.assertFalse(user.belongs_to_messaging_domain())

    def test_web_user_with_messaging_domain_returns_true(self):
        user = WebUser(domains=['domain_no_messaging_1', 'domain_with_messaging', 'domain_no_messaging_2'])
        self.assertTrue(user.belongs_to_messaging_domain())

    def test_commcare_user_is_compatible(self):
        user = CommCareUser(domain='domain_no_messaging_1')
        self.assertFalse(user.belongs_to_messaging_domain())

    def setUp(self):
        self.domains = {
            'domain_no_messaging_1': Domain(granted_messaging_access=False),
            'domain_no_messaging_2': Domain(granted_messaging_access=False),
            'domain_with_messaging': Domain(granted_messaging_access=True),
        }

        patcher = patch.object(Domain, 'get_by_name', side_effect=self._get_domain_by_name)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _get_domain_by_name(self, name):
        return self.domains[name]


class DeviceAppMetaMergeTests(SimpleTestCase):
    def test_overwrites_key(self):
        self.original_meta.num_unsent_forms = 5
        self.updates_meta.num_unsent_forms = 2

        self.original_meta.merge(self.updates_meta)
        self.assertEqual(self.original_meta.num_unsent_forms, 2)

    def test_ignores_older_submissions(self):
        recent_meta = DeviceAppMeta(num_unsent_forms=5, last_request=self.current_time)
        older_meta = DeviceAppMeta(num_unsent_forms=2, last_request=self.previous_time)

        recent_meta.merge(older_meta)
        self.assertEqual(recent_meta.num_unsent_forms, 5)

    def test_ignores_simultaneous_submissions(self):
        meta1 = DeviceAppMeta(num_unsent_forms=5, last_request=self.current_time)
        meta2 = DeviceAppMeta(num_unsent_forms=2, last_request=self.current_time)

        meta1.merge(meta2)
        self.assertEqual(meta1.num_unsent_forms, 5)

    def test_merges_new_properties(self):
        self.updates_meta.num_unsent_forms = 5

        self.original_meta.merge(self.updates_meta)
        self.assertEqual(self.original_meta.num_unsent_forms, 5)

    def test_merges_new_dates(self):
        self.updates_meta.last_heartbeat = self.current_time

        self.original_meta.merge(self.updates_meta)
        self.assertEqual(self.original_meta.last_heartbeat, self.current_time)

    def test_does_not_overwrite_unspecified_properties(self):
        self.original_meta.num_unsent_forms = 5

        self.original_meta.merge(self.updates_meta)
        self.assertEqual(self.original_meta.num_unsent_forms, 5)

    def test_uses_nontruthy_values(self):
        self.original_meta.num_unsent_forms = 5
        self.updates_meta.num_unsent_forms = 0

        self.original_meta.merge(self.updates_meta)
        self.assertEqual(self.original_meta.num_unsent_forms, 0)

    def test_updates_dates(self):
        self.original_meta.last_heartbeat = self.previous_time
        self.updates_meta.last_heartbeat = self.current_time

        self.original_meta.merge(self.updates_meta)
        self.assertEqual(self.original_meta.last_heartbeat, self.current_time)

    def test_ignores_older_dates(self):
        self.original_meta.num_unsent_forms = 5
        self.original_meta.last_heartbeat = self.current_time

        self.updates_meta.num_unsent_forms = 2
        self.updates_meta.last_heartbeat = self.previous_time

        self.original_meta.merge(self.updates_meta)
        self.assertEqual(self.original_meta.num_unsent_forms, 2)  # Normal values should still merge
        # But the older time should be ignored
        self.assertEqual(self.original_meta.last_heartbeat, self.current_time)

    def test_updates_last_request(self):
        original_meta = DeviceAppMeta(last_request=self.previous_time)
        updates_meta = DeviceAppMeta(last_heartbeat=self.current_time)

        original_meta.merge(updates_meta)
        self.assertEqual(original_meta.last_request, self.current_time)

    def setUp(self):
        self.previous_time = datetime(2022, 10, 2)
        self.current_time = self.previous_time + timedelta(hours=1)

        self.original_meta = DeviceAppMeta(last_request=self.previous_time)
        self.updates_meta = DeviceAppMeta(last_request=self.current_time)


class DeviceAppMetaLatestRequestTests(SimpleTestCase):
    def test_uses_max_from_submission(self):
        meta = DeviceAppMeta(
            last_submission=self.current_time,
            last_sync=self.previous_time,
            last_heartbeat=self.previous_time
        )
        meta._update_latest_request()
        self.assertEqual(meta.last_request, self.current_time)

    def test_uses_max_from_sync(self):
        meta = DeviceAppMeta(
            last_sync=self.current_time,
            last_submission=self.previous_time,
            last_heartbeat=self.previous_time
        )
        meta._update_latest_request()
        self.assertEqual(meta.last_request, self.current_time)

    def test_uses_max_from_heartbeat(self):
        meta = DeviceAppMeta(
            last_heartbeat=self.current_time,
            last_submission=self.previous_time,
            last_sync=self.previous_time
        )
        meta._update_latest_request()
        self.assertEqual(meta.last_request, self.current_time)

    def setUp(self):
        self.previous_time = datetime(2022, 10, 2)
        self.current_time = self.previous_time + timedelta(hours=1)
