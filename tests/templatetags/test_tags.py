"""Template tags for unit tests."""
from django import template
from django.template import Template
from argcache import registry
from argcache.extras.template import cache_inclusion_tag
from ..models import Article, Reporter

register = template.Library()

SILLY_TEMPLATE = Template("{{ x.arg }} {{ x.counter }}")

# Counts how many times SillyObject.counter() has been called.
counter = [0]


class SillyObject(object):
    def __init__(self, arg):
        self.arg = arg

    def counter(self):
        counter[0] += 1
        return counter[0]


@cache_inclusion_tag(register, SILLY_TEMPLATE)
def silly_inclusion_tag(arg):
    return {'x': SillyObject(arg)}
silly_inclusion_tag.cached_function.depend_on_model(Article)
silly_inclusion_tag.cached_function.depend_on_row(
    Reporter, lambda reporter: {'arg': reporter.first_name})
