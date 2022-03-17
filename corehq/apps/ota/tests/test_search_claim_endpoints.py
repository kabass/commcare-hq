import re
from uuid import uuid4

from django.test import Client, TestCase
from django.urls import reverse

from flaky import flaky

from casexml.apps.case.mock import CaseBlock
from casexml.apps.case.tests.util import delete_all_cases
from casexml.apps.case.util import post_case_blocks
from dimagi.utils.couch.cache.cache_core import get_redis_default_cache
from pillowtop.es_utils import initialize_index_and_mapping

from corehq.apps.case_search.models import (
    CASE_SEARCH_XPATH_QUERY_KEY,
    CLAIM_CASE_TYPE,
    CaseSearchConfig,
)
from corehq.apps.domain.shortcuts import create_domain
from corehq.apps.es.tests.utils import es_test
from corehq.apps.users.models import CommCareUser
from corehq.elastic import get_es_new
from corehq.form_processor.models import CommCareCase
from corehq.pillows.case_search import (
    CaseSearchReindexerFactory,
    domains_needing_search_index,
)
from corehq.pillows.mappings.case_search_mapping import (
    CASE_SEARCH_INDEX,
    CASE_SEARCH_INDEX_INFO,
)
from corehq.util.elastic import ensure_index_deleted
from corehq.util.test_utils import flag_enabled

DOMAIN = 'swashbucklers'
USERNAME = 'testy_mctestface'
PASSWORD = '123'
CASE_NAME = 'Jamie Hand'
CASE_TYPE = 'case'
OWNER_ID = 'nerc'
TIMESTAMP = '2016-04-17T10:13:06.588694Z'
FIXED_DATESTAMP = '2016-04-17'
PATTERN = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z'
DATE_PATTERN = r'\d{4}-\d{2}-\d{2}'

# cf. http://www.theguardian.com/environment/2016/apr/17/boaty-mcboatface-wins-poll-to-name-polar-research-vessel


@es_test
@flag_enabled("SYNC_SEARCH_CASE_CLAIM")
class CaseClaimEndpointTests(TestCase):
    def setUp(self):
        self.domain = create_domain(DOMAIN)
        self.user = CommCareUser.create(DOMAIN, USERNAME, PASSWORD, None, None)
        initialize_index_and_mapping(get_es_new(), CASE_SEARCH_INDEX_INFO)
        CaseSearchConfig.objects.get_or_create(pk=DOMAIN, enabled=True)
        delete_all_cases()
        self.case_id = uuid4().hex
        _, [self.case] = post_case_blocks([CaseBlock(
            create=True,
            case_id=self.case_id,
            case_type=CASE_TYPE,
            case_name=CASE_NAME,
            external_id=CASE_NAME,
            user_id=OWNER_ID,
            owner_id=OWNER_ID,
            update={'opened_by': OWNER_ID},
        ).as_xml()], {'domain': DOMAIN})
        domains_needing_search_index.clear()
        CaseSearchReindexerFactory(domain=DOMAIN).build().reindex()
        es = get_es_new()
        es.indices.refresh(CASE_SEARCH_INDEX)

    def tearDown(self):
        ensure_index_deleted(CASE_SEARCH_INDEX)
        self.user.delete(self.domain.name, deleted_by=None)
        self.domain.delete()
        cache = get_redis_default_cache()
        cache.clear()

    def test_claim_case(self):
        """
        A claim case request should create an extension case
        """
        self.assertEqual(len(CommCareCase.objects.get_case_ids_in_domain(DOMAIN, CLAIM_CASE_TYPE)), 0)

        client = Client()
        client.login(username=USERNAME, password=PASSWORD)
        url = reverse('claim_case', kwargs={'domain': DOMAIN})
        client.post(url, {'case_id': self.case_id})

        claim_ids = CommCareCase.objects.get_case_ids_in_domain(DOMAIN, CLAIM_CASE_TYPE)
        self.assertEqual(len(claim_ids), 1)
        claim = CommCareCase.objects.get_case(claim_ids[0], DOMAIN)
        self.assertEqual(claim.owner_id, self.user.get_id)
        self.assertEqual(claim.name, CASE_NAME)

    def test_duplicate_client_claim(self):
        """
        Server should not allow the same client to claim the same case more than once
        """
        client = Client()
        client.login(username=USERNAME, password=PASSWORD)
        url = reverse('claim_case', kwargs={'domain': DOMAIN})
        # First claim
        response = client.post(url, {'case_id': self.case_id})
        self.assertEqual(response.status_code, 200)
        # Dup claim
        response = client.post(url, {'case_id': self.case_id})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.content.decode('utf-8'), 'You have already claimed that case')

    def test_duplicate_user_claim(self):
        """
        Server should not allow the same user to claim the same case more than once
        """
        client1 = Client()
        client1.login(username=USERNAME, password=PASSWORD)
        url = reverse('claim_case', kwargs={'domain': DOMAIN})
        # First claim
        response = client1.post(url, {'case_id': self.case_id})
        self.assertEqual(response.status_code, 200)
        # Dup claim
        client2 = Client()
        client2.login(username=USERNAME, password=PASSWORD)
        response = client2.post(url, {'case_id': self.case_id})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.content.decode('utf-8'), 'You have already claimed that case')

    @flaky
    def test_claim_restore_as(self):
        """Server should assign cases to the correct user
        """
        client = Client()
        client.login(username=USERNAME, password=PASSWORD)
        other_user_username = 'other_user@{}.commcarehq.org'.format(DOMAIN)
        other_user = CommCareUser.create(DOMAIN, other_user_username, PASSWORD, None, None)

        url = reverse('claim_case', kwargs={'domain': DOMAIN})

        client.post(url, {
            'case_id': self.case_id,
            'commcare_login_as': other_user_username
        })

        claim_ids = CommCareCase.objects.get_case_ids_in_domain(DOMAIN, CLAIM_CASE_TYPE)
        self.assertEqual(len(claim_ids), 1)

        claim_case = CommCareCase.objects.get_case(claim_ids[0], DOMAIN)
        self.assertEqual(claim_case.owner_id, other_user._id)

    def test_claim_restore_as_proper_cache(self):
        """Server should assign cases to the correct user
        """
        client = Client()
        client.login(username=USERNAME, password=PASSWORD)
        other_user_username = 'other_user@{}.commcarehq.org'.format(DOMAIN)
        other_user = CommCareUser.create(DOMAIN, other_user_username, PASSWORD, None, None)

        another_user_username = 'another_user@{}.commcarehq.org'.format(DOMAIN)
        another_user = CommCareUser.create(DOMAIN, another_user_username, PASSWORD, None, None)

        url = reverse('claim_case', kwargs={'domain': DOMAIN})

        client.post(url, {
            'case_id': self.case_id,
            'commcare_login_as': other_user_username
        })

        claim_ids = CommCareCase.objects.get_case_ids_in_domain(DOMAIN, CLAIM_CASE_TYPE)
        self.assertEqual(len(claim_ids), 1)

        claim_case = CommCareCase.objects.get_case(claim_ids[0], DOMAIN)
        self.assertEqual(claim_case.owner_id, other_user._id)

        client.post(url, {
            'case_id': self.case_id,
            'commcare_login_as': another_user_username
        })

        # We've now created two claims
        claim_ids = CommCareCase.objects.get_case_ids_in_domain(DOMAIN, CLAIM_CASE_TYPE)
        self.assertEqual(len(claim_ids), 2)

        # The most recent one should be the extension owned by the other user
        claim_cases = CommCareCase.objects.get_cases(claim_ids, DOMAIN)
        self.assertIn(another_user._id, [case.owner_id for case in claim_cases])

    def test_search_endpoint(self):
        self.maxDiff = None
        client = Client()
        client.login(username=USERNAME, password=PASSWORD)
        url = reverse('remote_search', kwargs={'domain': DOMAIN})

        matching_criteria = [
            {'name': 'Jamie Hand'},
            {'name': 'Jamie Hand', CASE_SEARCH_XPATH_QUERY_KEY: 'date_opened > "2015-03-25"'},
            {CASE_SEARCH_XPATH_QUERY_KEY: 'name = "not Jamie" or name = "Jamie Hand"'},
            {CASE_SEARCH_XPATH_QUERY_KEY: ['name = "Jamie Hand"', 'date_opened > "2015-03-25"']},
        ]
        for params in matching_criteria:
            params.update({'case_type': CASE_TYPE})
            response = client.get(url, params)
            self._assert_known_search_result(response, params)

        non_matching_criteria = [
            {'name': 'Jamie Face'},
            {'name': 'Jamie Hand', CASE_SEARCH_XPATH_QUERY_KEY: 'date_opened < "2015-03-25"'},
            {CASE_SEARCH_XPATH_QUERY_KEY: 'name = "not Jamie" and name = "Jamie Hand"'},
            {CASE_SEARCH_XPATH_QUERY_KEY: ['name = "Jamie Face"', 'date_opened < "2015-03-25"']},
        ]
        for params in non_matching_criteria:
            params.update({'case_type': CASE_TYPE})
            response = client.get(url, params)
            self._assert_empty_search_result(response, params)

    def _assert_known_search_result(self, response, message=None):
        self.assertEqual(response.status_code, 200, message)
        known_result = (
            '<results id="case">'  # ("case" is not the case type)
            '<case case_id="{case_id}" '
            'case_type="{case_type}" '
            'owner_id="{owner_id}" '
            'status="open">'
            '<case_name>{case_name}</case_name>'
            '<last_modified>2016-04-17T10:13:06.588694Z</last_modified>'
            '<external_id>Jamie Hand</external_id>'
            '<date_opened>2016-04-17</date_opened>'
            '<commcare_search_score>xxx</commcare_search_score>'
            '<opened_by>nerc</opened_by>'
            '</case>'
            '</results>'.format(
                case_id=self.case_id,
                case_name=CASE_NAME,
                case_type=CASE_TYPE,
                owner_id=OWNER_ID,
            ))
        score_regex = re.compile(r'(<commcare_search_score>)(\d+.\d+)(<\/commcare_search_score>)')
        self.assertEqual(
            score_regex.sub(r'\1xxx\3',
                            re.sub(DATE_PATTERN, FIXED_DATESTAMP,
                                   re.sub(PATTERN, TIMESTAMP, response.content.decode('utf-8')))),
            known_result,
            message)

    def _assert_empty_search_result(self, response, message=None):
        self.assertEqual(response.status_code, 200, message)
        self.assertEqual('<results id="case" />', response.content.decode('utf-8'), message)
