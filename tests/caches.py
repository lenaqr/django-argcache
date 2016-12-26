import time
from argcache.function import cache_function, depend_on_cache
from argcache.key_set import wildcard

# make sure cached inclusion tags are imported by the cache loader
from .templatetags import test_tags

# some test functions

counter = [0]
@cache_function
def get_calls(x):
    counter[0] += 1
    return counter[0]

def get_calls_reset():
    counter[0] = 0

@cache_function([
    depend_on_cache(get_calls, lambda x=wildcard: {'x': x})
])
def get_squared_calls(x):
    return get_calls(x)**2

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
