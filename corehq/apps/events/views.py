from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.http import HttpResponseRedirect

from corehq.apps.hqwebapp.views import CRUDPaginatedViewMixin
from corehq.apps.domain.views.base import BaseDomainView
from corehq.apps.events.models import (
    Event,
    get_domain_events,
)
from corehq.apps.events.forms import CreateEventForm
from corehq.apps.hqwebapp.decorators import use_jquery_ui


class EventsView(BaseDomainView, CRUDPaginatedViewMixin):
    urlname = "events_page"
    template_name = 'events_list.html'

    section_name = _("Events")
    page_title = _("Attendance Tracking Events")
    limit_text = _("events per page")
    empty_notification = _("You have no events")
    loading_message = _("Loading events")

    @property
    def section_url(self):
        return reverse(self.urlname, args=(self.domain,))

    @property
    def page_url(self):
        return reverse(self.urlname, args=(self.domain,))

    @property
    def total(self):
        return len(self.domain_events)

    @property
    def column_names(self):
        return [
            _("Name"),
            _("Start date"),
            _("End date"),
            _("Attendance Target"),
            _("Total attendees"),
            _("Status"),
        ]

    @property
    def page_context(self):
        context = self.pagination_context
        return context

    @property
    def domain_events(self):
        return get_domain_events(self.domain)

    @property
    def paginated_list(self):
        start, end = self.skip, self.skip + self.limit
        for event in self.domain_events[start:end]:
            yield {
                'itemData': self._format_paginated_event(event),
                'template': 'base-event-template'
            }

    def post(self, *args, **kwargs):
        return self.paginate_crud_response

    def _format_paginated_event(self, event: Event):
        return {
            'id': event.case.case_id,
            'name': event.name,
            'start_date': str(event.start_date),
            'end_date': str(event.end_date),
            'target_attendance': event.attendance_target,
            'total_attendance': event.total_attendance,
            'status': event.status,
        }


class EventCreateView(BaseDomainView):
    template_name = "new_event.html"
    urlname = 'add_attendance_tracking_event'
    page_title = _("Add Attendance Tracking Event")
    section_name = _("New Tracking Event")

    @use_jquery_ui
    def dispatch(self, request, *args, **kwargs):
        return super(EventCreateView, self).dispatch(request, *args, **kwargs)

    @property
    def section_url(self):
        return reverse(self.urlname, args=(self.domain,))

    def get_context_data(self, **kwargs):
        return {'form': self.form}

    def post(self, *args, **kwargs):
        form = self.form

        if form.is_valid():
            event_data = form.cleaned_data
            event_data['domain'] = self.domain
            event_data['manager'] = self.request.couch_user

            event = Event.get_obj_from_data(event_data)
            event.save()
            return HttpResponseRedirect(reverse(EventsView.urlname, args=(self.domain,)))

        return self.get(self.request, *args, **kwargs)

    @property
    def form(self):
        if self.request.method == 'POST':
            return CreateEventForm(self.request.POST)
        else:
            return CreateEventForm(initial={})
