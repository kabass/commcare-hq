import json
from corehq.apps.fixtures.models import LookupTable, LookupTableRow
from corehq.apps.reports.filters.base import BaseReportFilter
from django.urls import reverse


class AsyncDrillableFilter(BaseReportFilter):
    # todo: add documentation
    # todo: cleanup template
    """
    example_hierarchy = [{"type": "state", "display": "name"},
                         {"type": "district", "parent_ref": "state_id", "references": "id", "display": "name"},
                         {"type": "block", "parent_ref": "district_id", "references": "id", "display": "name"},
                         {"type": "village", "parent_ref": "block_id", "references": "id", "display": "name"}]
    """
    template = "custom/reports/mc/reports/templates/mc/reports/drillable_async.html"
    # a list of fixture data type names that representing different levels of the hierarchy. Starting with the root
    hierarchy = []

    def fdi_to_json(self, fdi):
        return {
            'fixture_type': fdi.table_id.hex,
            'fields': fdi.fields_without_attributes,
            'id': fdi.id.hex,
            'children': getattr(fdi, '_children', None),
        }

    fdts = {}

    def data_types(self, index=None):
        if not self.fdts:
            self.fdts = [
                LookupTable.objects.by_domain_tag(self.domain, h["type"])
                for h in self.hierarchy
            ]
        return self.fdts if index is None else self.fdts[index]

    @property
    def api_root(self):
        return reverse('api_dispatch_list', kwargs={'domain': self.domain,
                                                    'resource_name': 'fixture_internal',
                                                    'api_name': 'v0.5'})

    @property
    def full_hierarchy(self):
        ret = []
        for i, h in enumerate(self.hierarchy):
            new_h = dict(h)
            new_h['id'] = self.data_types(i).id.hex
            ret.append(new_h)
        return ret

    def generate_lineage(self, leaf_type, leaf_item_id):
        leaf_fdi = LookupTableRow.objects.get(id=leaf_item_id)

        index = None
        for i, h in enumerate(self.hierarchy[::-1]):
            if h["type"] == leaf_type:
                index = i

        if index is None:
            raise Exception(
                "Could not generate lineage for AsyncDrillableFilter due to a nonexistent leaf_type (%s)"
                % leaf_type)

        lineage = [leaf_fdi]
        for i, h in enumerate(self.full_hierarchy[::-1]):
            if i < index or i >= len(self.hierarchy) - 1:
                continue
            real_index = len(self.hierarchy) - (i + 1)
            lineage.insert(
                0, LookupTableRow.objects.with_value(
                    self.domain,
                    self.data_types(real_index - 1).id,
                    h["references"],
                    lineage[0].fields_without_attributes[h["parent_ref"]]
                ).get())

        return lineage

    @property
    def filter_context(self):
        root_fdis = [self.fdi_to_json(f) for f in LookupTableRow.objects.iter_sorted(
            self.domain, self.data_types(0).id)]

        f_id = self.request.GET.get('fixture_id', None)
        selected_fdi_type = f_id.split(':')[0] if f_id else None
        selected_fdi_id = f_id.split(':')[1] if f_id else None

        if selected_fdi_id:
            lineage = self.generate_lineage(selected_fdi_type, selected_fdi_id)
            parent = {'children': root_fdis}
            for i, fdi in enumerate(lineage[:-1]):
                this_fdi = [f for f in parent['children']
                            if f['id'] == fdi.get_id][0]
                next_h = self.hierarchy[i + 1]
                this_fdi['children'] = [self.fdi_to_json(f) for f in
                                        LookupTableRow.objects.with_value(
                                            self.domain,
                                            self.data_types(i + 1).id,
                                            next_h["parent_ref"],
                                            fdi.fields_without_attributes[next_h["references"]])]
                parent = this_fdi

        return {
            'api_root': self.api_root,
            'control_name': self.label,
            'control_slug': self.slug,
            'selected_fdi_id': selected_fdi_id,
            'fdis': json.dumps(root_fdis),
            'hierarchy': self.full_hierarchy
        }
