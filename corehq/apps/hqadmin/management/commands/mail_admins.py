import sys
import warnings

from django.core.mail import mail_admins
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '[DEPRECATED] Send args as a one-shot email to the admins.'

    def add_arguments(self, parser):
        parser.add_argument(
            'message',
            nargs='*',
        )
        parser.add_argument('--subject', help='Subject', default='Mail from the console'),
        parser.add_argument('--stdin', action='store_true', default=False, help='Read message body from stdin'),
        parser.add_argument('--html', action='store_true', default=False, help='HTML payload'),
        parser.add_argument('--environment', default='', help='The environment we are mailing about'),

    def handle(self, message, **options):
        warnings.warn(
            "mail_admins is deprecated. Use 'send_email --to-admins' instead.",
            DeprecationWarning,
        )
        if options['stdin']:
            message = sys.stdin.read()
        else:
            message = ' '.join(message)

        html = None
        if options['html']:
            html = message

        mail_admins(options['subject'], message, html_message=html)
