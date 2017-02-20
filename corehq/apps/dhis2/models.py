import httplib
import json
import logging
from collections import namedtuple

import requests

from dimagi.ext.couchdbkit import Document, DocumentSchema, StringProperty


COUCH_KEYS = ('_id', 'doc_type', '_rev', '#export_tag')


class Dhis2Connection(Document):
    domain = StringProperty()
    server_url = StringProperty()
    username = StringProperty()
    password = StringProperty()


class DataValueMap(Document):
    domain = StringProperty()
    report = StringProperty()  # a UCR
    # UCR columns to be mapped to DHIS2 DataValue properties:
    data_element_column = StringProperty(required=True)
    # period_column = StringProperty(required=True)  # MVP: report (month) period as YYYYMM
    org_unit_column = StringProperty(required=True)
    category_option_combo_column = StringProperty(required=True)
    value_column = StringProperty(required=True)
    complete_date_column = StringProperty()
    attribute_option_combo_column = StringProperty()  # (DHIS2 defaults this to categoryOptionCombo)
    comment_column = StringProperty()


# MVP: "monthly"
# class ReportPeriod(Document):
#     domain = StringProperty()
#     report = StringProperty()  # a UCR
#     period = StringProperty()
#     #  DHIS2 offers weekly, monthly, two-monthly, quarterly, six-monthly, financial-yearly & annually


class JsonApiError(Exception):
    """
    JsonApiError is raised for HTTP or socket errors.
    """
    pass


class Dhis2ApiQueryError(JsonApiError):
    """
    Dhis2ApiQueryError is raised when the API returns an unexpected response.
    """
    pass


class Dhis2ConfigurationError(Exception):
    """
    DHIS2 API Integration has not been configured correctly.
    """
    pass


class Dhis2IntegrationError(Exception):
    """
    A failure has occurred in CommCareHQ related to but not caused by DHIS2.
    """
    pass


def json_serializer(obj):
    """
    A JSON serializer that serializes dates, times, and namedtuples
    """
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    if hasattr(obj, '_asdict'):
        return obj._asdict()


class JsonApiRequest(object):
    """
    Wrap requests with URL, header and authentication for DHIS2 API
    """

    def __init__(self, server_url, username, password):
        self.server_url = server_url  # e.g. "https://dhis2.example.com/api/26/"
        self.headers = {'Accept': 'application/json'}
        self.auth = (username, password)

    @staticmethod
    def json_or_error(response):
        """
        Return HTTP status, JSON

        :raises JsonApiError: if HTTP status is not in the 200 (OK) range
        """
        if 200 <= response.status_code < 300:
            if response.content:
                return response.json()
            else:
                # Response has no body. Return a status in a way that is consistent with other requests
                return {
                    'status': 'SUCCESS',
                    'httpStatusCode': response.status_code,
                    'httpStatus': httplib.responses[response.status_code],
                }
        else:
            raise JsonApiError('API request to {} failed with HTTP status {}: {}'.format(
                response.url, response.status_code, response.text))

    def get(self, path, **kwargs):
        logging.debug(
            'DHIS2: GET %s: \n'
            '    Headers: %s\n'
            '    kwargs: %s',
            self.server_url + path, self.headers, kwargs
        )
        try:
            response = requests.get(self.server_url + path, headers=self.headers, auth=self.auth, **kwargs)
        except requests.RequestException as err:
            logging.exception(
                'JSON API raised HTTP or socket error.\n'
                'Request details: %s\n'
                'Error: %s',
                {'method': 'get', 'url': self.server_url + path, 'headers': self.headers},
                err)
            raise JsonApiError(str(err))
        return JsonApiRequest.json_or_error(response)

    def delete(self, path, **kwargs):
        logging.debug(
            'DHIS2: DELETE %s: \n'
            '    Headers: %s\n'
            '    kwargs: %s',
            self.server_url + path, self.headers, kwargs
        )
        try:
            response = requests.delete(self.server_url + path, headers=self.headers, auth=self.auth, **kwargs)
        except requests.RequestException as err:
            logging.exception(
                'JSON API raised HTTP or socket error.\n'
                'Request details: %s\n'
                'Error: %s',
                {'method': 'delete', 'url': self.server_url + path, 'headers': self.headers},
                err)
            raise JsonApiError(str(err))
        return JsonApiRequest.json_or_error(response)

    def post(self, path, data, **kwargs):
        # Make a copy of self.headers because setting content type on requests that don't send content is bad
        headers = self.headers.copy()
        headers['Content-type'] = 'application/json'
        json_data = json.dumps(data, default=json_serializer)
        logging.debug(
            'DHIS2: POST %s: \n'
            '    Headers: %s\n'
            '    Data: %s\n'
            '    kwargs: %s',
            self.server_url + path, self.headers, json_data, kwargs
        )
        try:
            response = requests.post(self.server_url + path, json_data, headers=headers, auth=self.auth, **kwargs)
        except requests.RequestException as err:
            logging.exception(
                'JSON API raised HTTP or socket error.\n'
                'Request details: %s\n'
                'Error: %s',
                {'method': 'post', 'url': self.server_url + path, 'data': json_data, 'headers': headers},
                err
            )
            raise JsonApiError(str(err))
        return JsonApiRequest.json_or_error(response)

    def put(self, path, data, **kwargs):
        headers = self.headers.copy()
        headers['Content-type'] = 'application/json'
        json_data = json.dumps(data, default=json_serializer)
        logging.debug(
            'DHIS2: PUT %s: \n'
            '    Headers: %s\n'
            '    Data: %s\n'
            '    kwargs: %s',
            self.server_url + path, self.headers, json_data, kwargs
        )
        try:
            response = requests.put(self.server_url + path, json_data, headers=headers, auth=self.auth, **kwargs)
        except requests.RequestException as err:
            logging.exception(
                'JSON API raised HTTP or socket error.\n'
                'Request details: %s\n'
                'Error: %s',
                {'method': 'put', 'url': self.server_url + path, 'data': json_data, 'headers': headers},
                err
            )
            raise JsonApiError(str(err))
        return JsonApiRequest.json_or_error(response)


class AsDictMixin(dict):
    def _asdict(self):
        # Used by json_serializer for sending to the API. Don't return CouchDB's properties
        return {k: v for k, v in dict(self).items() if k not in COUCH_KEYS}


class DataValue(DocumentSchema, AsDictMixin):
    # Use DocumentSchema because it conveniently handles optional properties
    dataElement = StringProperty()
    period = StringProperty()
    orgUnit = StringProperty()
    categoryOptionCombo = StringProperty()
    value = StringProperty()
    completeDate = StringProperty()
    attributeOptionCombo = StringProperty()
    comment = StringProperty()
