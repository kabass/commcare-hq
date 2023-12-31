from django.apps import AppConfig
from django.conf import settings

from corehq.preindex import ExtraPreindexPlugin

from .signals import connect_user_signals


class UsersAppConfig(AppConfig):
    name = 'corehq.apps.users'

    def ready(self):
        """Code to run with Django starts"""
        ExtraPreindexPlugin.register('users', __file__, settings.USERS_GROUPS_DB)
        connect_user_signals()
