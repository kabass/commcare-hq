import re
from abc import abstractmethod, ABCMeta

import sys
from django.utils.html import format_html, escape
from django.utils.safestring import mark_safe

from memoized import memoized

url_re = re.compile(
    r"""(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))"""
)


def _wrap_url(url):
    return format_html('<a href="{url}">{url}</a>', url=url)


def _get_url_segments(text):
    for chunk in url_re.split(text):
        # The match pattern contains multiple capture groups;
        # Because only one will be populated, we need to ignore the Nones
        if not chunk:
            continue
        elif url_re.match(chunk):
            yield _wrap_url(chunk)
        else:
            yield escape(chunk)


def mark_up_urls(text):
    """
    Add HTML markup to any links within the text.
    I.e. 'Go to http://www.google.com'
    becomes 'Go to <a href="http://www.google.com">http://www.google.com</a>'.
    """
    return mark_safe(''.join(_get_url_segments(text)))  # nosec: all segments are sanitized


def _shell_color_template(color_code):
    def inner(text):
        return "\033[%sm%s\033[0m" % (color_code, text)
    return inner

shell_red = _shell_color_template('31')
shell_green = _shell_color_template('32')


class SimpleTableWriter(object):
    """Helper class for writing tables to the console
    """
    def __init__(self, output=None, row_formatter=None):
        self.output = output or sys.stdout
        self.row_formatter = row_formatter or CSVRowFormatter()

    def write_table(self, headers, rows):
        self.write_headers(headers)
        self.write_rows(rows)

    def write_headers(self, headers):
        self.output.write(self.row_formatter.format_headers(headers))

    def write_rows(self, rows):
        for row in rows:
            self.output.write(self.row_formatter.format_row(row))


class RowFormatter(metaclass=ABCMeta):
    @abstractmethod
    def get_template(self, num_cols):
        raise NotImplementedError

    def format_headers(self, headers):
        return self.format_row(headers)

    def format_row(self, row):
        return self.get_template(len(row)).format(*row)


class CSVRowFormatter(RowFormatter):
    """Format rows as CSV"""

    def get_template(self, num_cols):
        return ','.join(['{}'] * num_cols)


class TableRowFormatter(RowFormatter):
    """Format rows as a table with optional row highlighting"""
    def __init__(self, col_widths=None, row_color_getter=None):
        self.col_widths = col_widths
        self.row_color_getter = row_color_getter

    @memoized
    def get_template(self, num_cols):
        if self.col_widths:
            assert len(self.col_widths) == num_cols
        else:
            self.col_widths = [20] * num_cols

        return ' | '.join(['{{:<{}}}'.format(width) for width in self.col_widths])

    def format_headers(self, headers):
        template = self.get_template(len(headers))
        return '{}\n{}'.format(
            template.format(*headers),
            template.format(*['-' * width for width in self.col_widths]),
        )

    def format_row(self, row):
        template = self.get_template(len(row))
        color = self.row_color_getter(row) if self.row_color_getter else None
        return self._highlight(color, template).format(*row)

    def _highlight(self, color, template):
        if not color:
            return template
        if color == 'red':
            return shell_red(template)
        if color == 'green':
            return shell_green(template)

        raise Exception('Unknown color: {}'.format(color))
