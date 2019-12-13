from datetime import timedelta

from dimagi.utils.parsing import string_to_utc_datetime

from corehq.motech.exceptions import ConfigurationError
from corehq.motech.openmrs.const import (
    ADDRESS_PROPERTIES,
    NAME_PROPERTIES,
    PERSON_PROPERTIES,
    PERSON_UUID_IDENTIFIER_TYPE_ID,
)
from corehq.motech.openmrs.repeater_helpers import (
    get_ancestor_location_openmrs_uuid,
    get_export_data,
    get_unknown_encounter_role,
    get_unknown_location_uuid,
)
from corehq.motech.openmrs.serializers import to_omrs_datetime
from corehq.motech.openmrs.workflow import WorkflowTask
from corehq.motech.value_source import as_value_source


class SyncPersonAttributesTask(WorkflowTask):

    def __init__(self, requests, info, openmrs_config, person_uuid, attributes):
        self.requests = requests
        self.info = info
        self.openmrs_config = openmrs_config
        self.person_uuid = person_uuid
        self.attributes = attributes

    def run(self):
        """
        Returns WorkflowTasks for creating and updating OpenMRS person attributes.
        """
        subtasks = []
        existing_person_attributes = {
            attribute['attributeType']['uuid']: (attribute['uuid'], attribute['value'])
            for attribute in self.attributes
        }
        for person_attribute_type, value_source_dict in self.openmrs_config.case_config.person_attributes.items():
            value_source = as_value_source(value_source_dict)
            if not value_source.can_export:
                continue
            value = value_source.get_value(self.info)
            if person_attribute_type in existing_person_attributes:
                attribute_uuid, existing_value = existing_person_attributes[person_attribute_type]
                if value != existing_value:
                    if value in ("", None):
                        subtasks.append(
                            DeletePersonAttributeTask(
                                self.requests, self.person_uuid, attribute_uuid, person_attribute_type,
                                existing_value
                            )
                        )
                    else:
                        subtasks.append(
                            UpdatePersonAttributeTask(
                                self.requests, self.person_uuid, attribute_uuid, person_attribute_type, value,
                                existing_value
                            )
                        )
            else:
                subtasks.append(
                    CreatePersonAttributeTask(self.requests, self.person_uuid, person_attribute_type, value)
                )
        return subtasks


class SyncPatientIdentifiersTask(WorkflowTask):

    def __init__(self, requests, info, openmrs_config, patient):
        self.requests = requests
        self.info = info
        self.openmrs_config = openmrs_config
        self.patient = patient

    def run(self):
        """
        Returns WorkflowTasks for creating and updating OpenMRS patient identifiers.
        """
        subtasks = []
        existing_patient_identifiers = {
            identifier['identifierType']['uuid']: (identifier['uuid'], identifier['identifier'])
            for identifier in self.patient['identifiers']
        }
        for patient_identifier_type, dict_ in self.openmrs_config.case_config.patient_identifiers.items():
            value_source = as_value_source(dict_)
            if not value_source.can_export:
                continue
            if patient_identifier_type == PERSON_UUID_IDENTIFIER_TYPE_ID:
                # Don't try to sync the OpenMRS person UUID; It's not a
                # user-defined identifier and it can't be changed.
                continue
            identifier = value_source.get_value(self.info)
            # If the patient is new, and its case property that
            # corresponds to the identifier is blank, then the
            # patient's identifier will have been generated by
            # repeater_helpers.generate_identifier(). The case will have
            # been updated by repeater_helpers.save_match_ids() but
            # self.info will not contain the newly-generated identifier.
            # `identifier` will be None. Don't try to update the
            # patient's identifier to None; it's already set correctly.
            if not identifier:
                continue
            if patient_identifier_type in existing_patient_identifiers:
                identifier_uuid, existing_identifier = existing_patient_identifiers[patient_identifier_type]
                if identifier != existing_identifier:
                    subtasks.append(
                        UpdatePatientIdentifierTask(
                            self.requests, self.patient['uuid'], identifier_uuid, patient_identifier_type,
                            identifier, existing_identifier
                        )
                    )
            else:
                subtasks.append(
                    CreatePatientIdentifierTask(
                        self.requests, self.patient['uuid'], patient_identifier_type, identifier
                    )
                )
        return subtasks


class CreateVisitsEncountersObsTask(WorkflowTask):

    def __init__(self, requests, domain, info, form_json, openmrs_config, person_uuid):
        self.requests = requests
        self.domain = domain
        self.info = info
        self.form_json = form_json
        self.openmrs_config = openmrs_config
        self.person_uuid = person_uuid

    def _get_start_stop_datetime(self, form_config):
        """
        Returns a start datetime for the Visit and the Encounter, and a
        stop_datetime for the Visit
        """
        if form_config.openmrs_start_datetime:
            value_source = as_value_source(form_config.openmrs_start_datetime)
            cc_start_datetime_str = value_source.get_commcare_value(self.info)
            if cc_start_datetime_str is None:
                raise ConfigurationError(
                    'A form config for form XMLNS "{}" uses "openmrs_start_datetime" to get the start of '
                    'the visit but no value was found in the form.'.format(form_config.xmlns)
                )
            try:
                cc_start_datetime = string_to_utc_datetime(cc_start_datetime_str)
            except ValueError:
                raise ConfigurationError(
                    'A form config for form XMLNS "{}" uses "openmrs_start_datetime" to get the start of '
                    'the visit but an invalid value was found in the form.'.format(form_config.xmlns)
                )
            cc_stop_datetime = cc_start_datetime + timedelta(days=1) - timedelta(seconds=1)
            # We need to serialize both values with the data type of
            # openmrs_start_datetime because they could be either
            # OpenMRS datetimes or OpenMRS dates, and their data
            # types must match.
            start_datetime = value_source.serialize(cc_start_datetime)
            stop_datetime = value_source.serialize(cc_stop_datetime)
        else:
            cc_start_datetime = string_to_utc_datetime(self.form_json['form']['meta']['timeEnd'])
            cc_stop_datetime = cc_start_datetime + timedelta(days=1) - timedelta(seconds=1)
            start_datetime = to_omrs_datetime(cc_start_datetime)
            stop_datetime = to_omrs_datetime(cc_stop_datetime)
        return start_datetime, stop_datetime

    def _get_values_for_concept(self, form_config):
        values_for_concept = {}
        for obs in form_config.openmrs_observations:
            if not obs.concept:
                # Skip ObservationMappings for importing all observations.
                continue
            value_source = as_value_source(obs.value)
            if value_source.can_export and not is_blank(value_source.get_value(self.info)):
                values_for_concept[obs.concept] = [value_source.get_value(self.info)]
        return values_for_concept

    def run(self):
        """
        Returns WorkflowTasks for creating visits, encounters and observations
        """
        subtasks = []
        provider_uuid = getattr(self.openmrs_config, 'openmrs_provider', None)
        location_uuid = (
            get_ancestor_location_openmrs_uuid(self.info)
            or get_unknown_location_uuid(self.requests)  # If we don't
            # set a location, OpenMRS sets it to NULL. That's OK for
            # OpenMRS, but it breaks Bahmni. Bahmni has an "Unknown
            # Location". Use that, if it exists.
        )
        for form_config in self.openmrs_config.form_configs:
            if form_config.xmlns == self.form_json['form']['@xmlns']:
                start_datetime, stop_datetime = self._get_start_stop_datetime(form_config)
                subtasks.append(
                    CreateVisitTask(
                        self.requests,
                        person_uuid=self.person_uuid,
                        provider_uuid=provider_uuid,
                        start_datetime=start_datetime,
                        stop_datetime=stop_datetime,
                        values_for_concept=self._get_values_for_concept(form_config),
                        encounter_type=form_config.openmrs_encounter_type,
                        openmrs_form=form_config.openmrs_form,
                        visit_type=form_config.openmrs_visit_type,
                        location_uuid=location_uuid,
                    )
                )
        return subtasks


class CreatePersonAttributeTask(WorkflowTask):

    def __init__(self, requests, person_uuid, attribute_type_uuid, value):
        self.requests = requests
        self.person_uuid = person_uuid
        self.attribute_type_uuid = attribute_type_uuid
        self.value = value
        self.attribute_uuid = None

    def run(self):
        response = self.requests.post(
            '/ws/rest/v1/person/{person_uuid}/attribute'.format(person_uuid=self.person_uuid),
            json={'attributeType': self.attribute_type_uuid, 'value': self.value},
            raise_for_status=True,
        )
        self.attribute_uuid = response.json()['uuid']

    def rollback(self):
        # if attribute_uuid is not set, it would be because the workflow task to create the attribute failed
        if self.attribute_uuid:
            self.requests.delete(
                '/ws/rest/v1/person/{person_uuid}/attribute/{attribute_uuid}'.format(
                    person_uuid=self.person_uuid, attribute_uuid=self.attribute_uuid
                ),
                raise_for_status=True,
            )


class DeletePersonAttributeTask(WorkflowTask):

    def __init__(self, requests, person_uuid, attribute_uuid, attribute_type_uuid, existing_value):
        self.requests = requests
        self.person_uuid = person_uuid
        self.attribute_uuid = attribute_uuid
        self.attribute_type_uuid = attribute_type_uuid
        self.existing_value = existing_value

    def run(self):
        self.requests.delete(
            '/ws/rest/v1/person/{person_uuid}/attribute/{attribute_uuid}'.format(
                person_uuid=self.person_uuid, attribute_uuid=self.attribute_uuid
            ),
            raise_for_status=True,
        )

    def rollback(self):
        self.requests.post(
            '/ws/rest/v1/person/{person_uuid}/attribute'.format(person_uuid=self.person_uuid),
            json={'attributeType': self.attribute_type_uuid, 'value': self.existing_value},
            raise_for_status=True,
        )


class UpdatePersonAttributeTask(WorkflowTask):

    def __init__(self, requests, person_uuid, attribute_uuid, attribute_type_uuid, value, existing_value):
        self.requests = requests
        self.person_uuid = person_uuid
        self.attribute_uuid = attribute_uuid
        self.attribute_type_uuid = attribute_type_uuid
        self.value = value
        self.existing_value = existing_value

    def run(self):
        self.requests.post(
            '/ws/rest/v1/person/{person_uuid}/attribute/{attribute_uuid}'.format(
                person_uuid=self.person_uuid, attribute_uuid=self.attribute_uuid
            ),
            json={
                'value': self.value,
                'attributeType': self.attribute_type_uuid,
            },
            raise_for_status=True,
        )

    def rollback(self):
        self.requests.post(
            '/ws/rest/v1/person/{person_uuid}/attribute/{attribute_uuid}'.format(
                person_uuid=self.person_uuid, attribute_uuid=self.attribute_uuid
            ),
            json={
                'value': self.existing_value,
                'attributeType': self.attribute_type_uuid,
            },
            raise_for_status=True,
        )


class CreatePatientIdentifierTask(WorkflowTask):

    def __init__(self, requests, patient_uuid, identifier_type_uuid, identifier):
        self.requests = requests
        self.patient_uuid = patient_uuid
        self.identifier_type_uuid = identifier_type_uuid
        self.identifier = identifier
        self.identifier_uuid = None

    def run(self):
        response = self.requests.post(
            '/ws/rest/v1/patient/{patient_uuid}/identifier'.format(patient_uuid=self.patient_uuid),
            json={'identifierType': self.identifier_type_uuid, 'identifier': self.identifier},
            raise_for_status=True,
        )
        self.identifier_uuid = response.json()['uuid']

    def rollback(self):
        if self.identifier_uuid:
            self.requests.delete(
                '/ws/rest/v1/patient/{patient_uuid}/identifier/{identifier_uuid}'.format(
                    patient_uuid=self.patient_uuid, identifier_uuid=self.identifier_uuid
                ),
                raise_for_status=True,
            )


class UpdatePatientIdentifierTask(WorkflowTask):

    def __init__(self, requests, patient_uuid, identifier_uuid, identifier_type_uuid, identifier,
                 existing_identifier):
        self.requests = requests
        self.patient_uuid = patient_uuid
        self.identifier_uuid = identifier_uuid
        self.identifier_type_uuid = identifier_type_uuid
        self.identifier = identifier
        self.existing_identifier = existing_identifier

    def run(self):
        self.requests.post(
            '/ws/rest/v1/patient/{patient_uuid}/identifier/{identifier_uuid}'.format(
                patient_uuid=self.patient_uuid, identifier_uuid=self.identifier_uuid
            ),
            json={
                'identifier': self.identifier,
                'identifierType': self.identifier_type_uuid,
            },
            raise_for_status=True,
        )

    def rollback(self):
        self.requests.post(
            '/ws/rest/v1/patient/{patient_uuid}/identifier/{identifier_uuid}'.format(
                patient_uuid=self.patient_uuid, identifier_uuid=self.identifier_uuid
            ),
            json={
                'identifier': self.existing_identifier,
                'identifierType': self.identifier_type_uuid,
            },
            raise_for_status=True,
        )


class CreateVisitTask(WorkflowTask):

    def __init__(self, requests, person_uuid, provider_uuid, start_datetime, stop_datetime, values_for_concept,
                 encounter_type, openmrs_form, visit_type, location_uuid=None):
        self.requests = requests
        self.person_uuid = person_uuid
        self.provider_uuid = provider_uuid
        self.start_datetime = start_datetime
        self.stop_datetime = stop_datetime
        self.values_for_concept = values_for_concept
        self.encounter_type = encounter_type
        self.openmrs_form = openmrs_form
        self.visit_type = visit_type
        self.location_uuid = location_uuid
        self.visit_uuid = None

    def run(self):
        subtasks = []
        if self.visit_type:
            visit = {
                'patient': self.person_uuid,
                'visitType': self.visit_type,
                'startDatetime': self.start_datetime,
                'stopDatetime': self.stop_datetime,
            }
            if self.location_uuid:
                visit['location'] = self.location_uuid
            response = self.requests.post('/ws/rest/v1/visit', json=visit, raise_for_status=True)
            self.visit_uuid = response.json()['uuid']

        subtasks.append(
            CreateEncounterTask(
                self.requests, self.person_uuid, self.provider_uuid, self.start_datetime, self.values_for_concept,
                self.encounter_type, self.openmrs_form, self.visit_uuid, self.location_uuid
            )
        )
        return subtasks

    def rollback(self):
        if self.visit_uuid:
            self.requests.delete('/ws/rest/v1/visit/{uuid}'.format(uuid=self.visit_uuid), raise_for_status=True)


class CreateEncounterTask(WorkflowTask):

    def __init__(self, requests, person_uuid, provider_uuid, start_datetime, values_for_concept, encounter_type,
                 openmrs_form, visit_uuid, location_uuid=None):
        self.requests = requests
        self.person_uuid = person_uuid
        self.provider_uuid = provider_uuid
        self.start_datetime = start_datetime
        self.values_for_concept = values_for_concept
        self.encounter_type = encounter_type
        self.openmrs_form = openmrs_form
        self.visit_uuid = visit_uuid
        self.location_uuid = location_uuid
        self.encounter_uuid = None

    def run(self):
        subtasks = []
        encounter = {
            'encounterDatetime': self.start_datetime,
            'patient': self.person_uuid,
            'encounterType': self.encounter_type,
        }
        if self.openmrs_form:
            encounter['form'] = self.openmrs_form
        if self.visit_uuid:
            encounter['visit'] = self.visit_uuid
        if self.location_uuid:
            encounter['location'] = self.location_uuid
        if self.provider_uuid:
            encounter_role = get_unknown_encounter_role(self.requests)
            encounter['encounterProviders'] = [{
                'provider': self.provider_uuid,
                'encounterRole': encounter_role['uuid']
            }]
        response = self.requests.post('/ws/rest/v1/encounter', json=encounter, raise_for_status=True)
        self.encounter_uuid = response.json()['uuid']

        for concept_uuid, values in self.values_for_concept.items():
            for value in values:
                subtasks.append(
                    CreateObsTask(
                        self.requests, self.encounter_uuid, concept_uuid, self.person_uuid, self.start_datetime,
                        value, self.location_uuid
                    )
                )
        return subtasks

    def rollback(self):
        if self.encounter_uuid:
            self.requests.delete(
                '/ws/rest/v1/encounter/{uuid}'.format(uuid=self.encounter_uuid), raise_for_status=True
            )


class CreateObsTask(WorkflowTask):

    def __init__(self, requests, encounter_uuid, concept_uuid, person_uuid, start_datetime, value,
                 location_uuid=None):
        self.requests = requests
        self.encounter_uuid = encounter_uuid
        self.concept_uuid = concept_uuid
        self.person_uuid = person_uuid
        self.start_datetime = start_datetime
        self.value = value
        self.location_uuid = location_uuid
        self.obs_uuid = None

    def run(self):
        observation = {
            'concept': self.concept_uuid,
            'person': self.person_uuid,
            'obsDatetime': self.start_datetime,
            'encounter': self.encounter_uuid,
            'value': self.value,
        }
        if self.location_uuid:
            observation['location'] = self.location_uuid
        response = self.requests.post('/ws/rest/v1/obs', json=observation, raise_for_status=True)
        self.obs_uuid = response.json()['uuid']

    def rollback(self):
        if self.obs_uuid:
            self.requests.delete('/ws/rest/v1/obs/{uuid}'.format(uuid=self.obs_uuid), raise_for_status=True)


class UpdatePersonNameTask(WorkflowTask):

    def __init__(self, requests, info, openmrs_config, person):
        self.requests = requests
        self.info = info
        self.openmrs_config = openmrs_config
        self.person = person
        self.person_uuid = person['uuid']
        self.name_uuid = person['preferredName']['uuid']

    def run(self):
        export_data = get_export_data(
            self.openmrs_config.case_config.person_preferred_name,
            NAME_PROPERTIES,
            self.info,
        )
        if export_data:
            self.requests.post(
                '/ws/rest/v1/person/{person_uuid}/name/{name_uuid}'.format(
                    person_uuid=self.person_uuid,
                    name_uuid=self.name_uuid,
                ),
                json=export_data,
                raise_for_status=True,
            )

    def rollback(self):
        """
        Reset the name changes back to their original values, which are
        taken from the patient details that OpenMRS returned at the
        start of the workflow.
        """
        properties = {
            property_: self.person['preferredName'].get(property_)
            for property_ in self.openmrs_config.case_config.person_preferred_name.keys()
            if property_ in NAME_PROPERTIES
        }
        if properties:
            self.requests.post(
                '/ws/rest/v1/person/{person_uuid}/name/{name_uuid}'.format(
                    person_uuid=self.person_uuid,
                    name_uuid=self.name_uuid,
                ),
                json=properties,
                raise_for_status=True,
            )


class CreatePersonAddressTask(WorkflowTask):

    def __init__(self, requests, info, openmrs_config, person):
        self.requests = requests
        self.info = info
        self.openmrs_config = openmrs_config
        self.person = person
        self.person_uuid = person['uuid']
        self.address_uuid = None

    def run(self):
        export_data = get_export_data(
            self.openmrs_config.case_config.person_preferred_address,
            ADDRESS_PROPERTIES,
            self.info,
        )
        if export_data:
            response = self.requests.post(
                '/ws/rest/v1/person/{person_uuid}/address/'.format(person_uuid=self.person_uuid),
                json=export_data,
                raise_for_status=True,
            )
            self.address_uuid = response.json()['uuid']

    def rollback(self):
        if self.address_uuid:
            self.requests.delete(
                '/ws/rest/v1/person/{person_uuid}/address/{address_uuid}'.format(
                    person_uuid=self.person_uuid,
                    address_uuid=self.address_uuid,
                ),
                raise_for_status=True,
            )


class UpdatePersonAddressTask(WorkflowTask):

    def __init__(self, requests, info, openmrs_config, person):
        self.requests = requests
        self.info = info
        self.openmrs_config = openmrs_config
        self.person = person
        self.person_uuid = person['uuid']
        self.address_uuid = person['preferredAddress']['uuid']

    def run(self):
        export_data = get_export_data(
            self.openmrs_config.case_config.person_preferred_address,
            ADDRESS_PROPERTIES,
            self.info,
        )
        if export_data:
            self.requests.post(
                '/ws/rest/v1/person/{person_uuid}/address/{address_uuid}'.format(
                    person_uuid=self.person_uuid,
                    address_uuid=self.address_uuid,
                ),
                json=export_data,
                raise_for_status=True,
            )

    def rollback(self):
        properties = {
            property_: self.person['preferredAddress'].get(property_)
            for property_ in self.openmrs_config.case_config.person_preferred_address.keys()
            if property_ in ADDRESS_PROPERTIES
        }
        if properties:
            self.requests.post(
                '/ws/rest/v1/person/{person_uuid}/address/{address_uuid}'.format(
                    person_uuid=self.person_uuid,
                    address_uuid=self.address_uuid,
                ),
                json=properties,
                raise_for_status=True,
            )


class UpdatePersonPropertiesTask(WorkflowTask):

    def __init__(self, requests, info, openmrs_config, person):
        self.requests = requests
        self.info = info
        self.openmrs_config = openmrs_config
        self.person = person

    def run(self):
        export_data = get_export_data(
            self.openmrs_config.case_config.person_properties,
            PERSON_PROPERTIES,
            self.info,
        )
        if export_data:
            self.requests.post(
                '/ws/rest/v1/person/{person_uuid}'.format(person_uuid=self.person['uuid']),
                json=export_data,
                raise_for_status=True,
            )

    def rollback(self):
        """
        Reset person properties back to their original values, which
        are taken from the patient details that OpenMRS returned at the
        start of the workflow.
        """
        properties = {
            property_: self.person.get(property_)
            for property_ in self.openmrs_config.case_config.person_properties.keys()
            if property_ in PERSON_PROPERTIES
        }
        if properties:
            self.requests.post(
                '/ws/rest/v1/person/{person_uuid}'.format(person_uuid=self.person['uuid']),
                json=properties,
                raise_for_status=True,
            )


# TODO: Refactor once https://github.com/dimagi/commcare-hq/pull/25732 is merged
def is_blank(value):
    """
    Returns True if ``value`` is ``None`` or an empty string.
    >>> is_blank("")
    True
    >>> is_blank(0)
    False
    >>> is_blank([])
    False
    """
    return value is None or value == ""
