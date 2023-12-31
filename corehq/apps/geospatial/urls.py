from django.conf.urls import re_path as url

from .dispatchers import CaseManagementMapDispatcher
from .views import geospatial_default, GeoPolygonView

urlpatterns = [
    url(r'^edit_geo_polygon/$', GeoPolygonView.as_view(),
        name=GeoPolygonView.urlname),
    url(r'^$', geospatial_default, name='geospatial_default'),
    CaseManagementMapDispatcher.url_pattern(),
]
