import uuid

from django.test import TestCase

from casexml.apps.case.mock import CaseFactory, CaseIndex, CaseStructure
from casexml.apps.case.tests.util import delete_all_cases, delete_all_xforms

from corehq.apps.userreports.expressions.factory import ExpressionFactory
from corehq.apps.userreports.specs import EvaluationContext


class IndexedCaseExpressionTest(TestCase):
    def setUp(self):
        super(IndexedCaseExpressionTest, self).setUp()
        self.domain = uuid.uuid4().hex
        self.factory = CaseFactory(domain=self.domain)
        self.context = EvaluationContext({"domain": self.domain})

    def tearDown(self):
        delete_all_xforms()
        delete_all_cases()
        super(IndexedCaseExpressionTest, self).tearDown()

    def test_parent_case_no_index(self):
        parent_id = uuid.uuid4().hex
        child_id = uuid.uuid4().hex
        [child, parent] = self.factory.create_or_update_case(CaseStructure(
            case_id=child_id,
            indices=[
                CaseIndex(CaseStructure(case_id=parent_id, attrs={'create': True}))
            ],
            attrs={'create': True}
        ))
        spec = {
            'type': 'nested',
            'argument_expression': {
                'type': 'indexed_case',
                'case_expression': {
                    'type': 'identity'
                }
            },
            'value_expression': {
                'type': 'property_name',
                'property_name': '_id'
            }
        }
        self.assertEqual(
            ExpressionFactory.from_spec(spec)(child.to_json(), self.context),
            parent_id
        )

    def test_named_index(self):
        parent_id = uuid.uuid4().hex
        child_id = uuid.uuid4().hex
        [child, parent] = self.factory.create_or_update_case(CaseStructure(
            case_id=child_id,
            indices=[
                CaseIndex(CaseStructure(case_id=parent_id, attrs={'create': True}),
                          identifier='mother')
            ],
            attrs={'create': True}
        ))
        spec = {
            'type': 'nested',
            'argument_expression': {
                'type': 'indexed_case',
                'case_expression': {
                    'type': 'identity'
                },
                'index': 'mother'
            },
            'value_expression': {
                'type': 'property_name',
                'property_name': '_id'
            }
        }
        self.assertEqual(
            ExpressionFactory.from_spec(spec)(child.to_json(), self.context),
            parent_id
        )

    def test_multiple_indexes(self):
        parent_id1 = uuid.uuid4().hex
        parent_id2 = uuid.uuid4().hex
        child_id = uuid.uuid4().hex
        [child, parent1, parent2] = self.factory.create_or_update_case(CaseStructure(
            case_id=child_id,
            indices=[
                CaseIndex(CaseStructure(case_id=parent_id1, attrs={'create': True}),
                          identifier='parent1'),
                CaseIndex(CaseStructure(case_id=parent_id2, attrs={'create': True}),
                          identifier='parent2')
            ],
            attrs={'create': True}
        ))
        spec = {
            'type': 'nested',
            'argument_expression': {
                'type': 'indexed_case',
                'case_expression': {
                    'type': 'identity'
                },
                'index': 'parent1'
            },
            'value_expression': {
                'type': 'property_name',
                'property_name': '_id'
            }
        }
        self.assertEqual(
            ExpressionFactory.from_spec(spec)(child.to_json(), self.context),
            parent_id1
        )

        spec['argument_expression']['index'] = 'parent2'
        self.assertEqual(
            ExpressionFactory.from_spec(spec)(child.to_json(), self.context),
            parent_id2
        )

    def test_grandparent_index(self):
        household_id = uuid.uuid4().hex
        parent_id = uuid.uuid4().hex
        child_id = uuid.uuid4().hex

        parent_case_structure = CaseStructure(
            case_id=parent_id,
            indices=[
                CaseIndex(CaseStructure(case_id=household_id, attrs={'create': True}),
                          identifier='household')
            ],
            attrs={'create': True}
        )
        [child, parent, household] = self.factory.create_or_update_case(CaseStructure(
            case_id=child_id,
            indices=[CaseIndex(parent_case_structure)],
            attrs={'create': True}
        ))

        spec = {
            'type': 'nested',
            'argument_expression': {
                'type': 'indexed_case',
                'case_expression': {
                    'type': 'indexed_case',
                    'case_expression': {
                        'type': 'identity'
                    },
                    'index': 'parent'
                },
                'index': 'household',
            },
            'value_expression': {
                'type': 'property_name',
                'property_name': '_id'
            }
        }
        self.assertEqual(
            ExpressionFactory.from_spec(spec)(child.to_json(), self.context),
            household_id
        )
