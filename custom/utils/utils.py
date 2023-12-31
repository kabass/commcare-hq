from corehq.apps.reports.util import get_INFilter_element_bindparam


def clean_IN_filter_value(filter_values, filter_value_name):
    if filter_value_name in filter_values:
        for i, val in enumerate(filter_values[filter_value_name]):
            filter_values[get_INFilter_element_bindparam(filter_value_name, i)] = val
        del filter_values[filter_value_name]
    return filter_values
