import time
from argcache.function import cache_function

# make sure cached inclusion tags are imported by the cache loader
from .templatetags import test_tags

# some test functions

counter = [0]
@cache_function
def get_calls(x):
    counter[0] += 1
    return counter[0]

value = [0]
def set_value(x):
    value[0] = x
    get_value.delete_all()

@cache_function
def get_value():
    return value[0]

@cache_function
def get_value_slowly():
    x = get_value()
    time.sleep(1)
    return x
get_value_slowly.depend_on_cache(get_value, lambda: {})
