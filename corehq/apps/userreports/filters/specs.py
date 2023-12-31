from django.utils.translation import gettext as _

from jsonobject.base import DefaultProperty

from dimagi.ext.jsonobject import (
    DictProperty,
    JsonObject,
    ListProperty,
    StringProperty,
)

from corehq.apps.userreports.exceptions import BadSpecError
from corehq.apps.userreports.expressions.getters import (
    getter_from_property_reference,
)
from corehq.apps.userreports.mixins import NoPropertyTypeCoercionMixIn
from corehq.apps.userreports.operators import OPERATORS
from corehq.apps.userreports.specs import TypeProperty


class BaseFilterSpec(JsonObject):
    _allow_dynamic_properties = False
    comment = StringProperty()


class BooleanExpressionFilterSpec(NoPropertyTypeCoercionMixIn, BaseFilterSpec):
    type = TypeProperty('boolean_expression')
    operator = StringProperty(choices=list(OPERATORS), required=True)
    property_value = DefaultProperty()
    expression = DefaultProperty(required=True)

    @classmethod
    def wrap(cls, obj):
        _assert_prop_in_obj('property_value', obj)
        return super(BooleanExpressionFilterSpec, cls).wrap(obj)


class PropertyMatchFilterSpec(BaseFilterSpec):
    type = TypeProperty('property_match')
    property_name = StringProperty()
    property_path = ListProperty()
    property_value = DefaultProperty()

    @property
    def getter(self):
        return getter_from_property_reference(self)

    @classmethod
    def wrap(cls, obj):
        _assert_prop_in_obj('property_value', obj)
        return super(PropertyMatchFilterSpec, cls).wrap(obj)


class NotFilterSpec(BaseFilterSpec):
    type = TypeProperty('not')
    filter = DictProperty()  # todo: validators=FilterFactory.validate_spec


class NamedFilterSpec(BaseFilterSpec):
    type = TypeProperty('named')
    name = StringProperty(required=True)


def _assert_prop_in_obj(property_name, obj):
    if property_name not in obj:
        raise BadSpecError(_('{} is required!'.format(property_name)))
