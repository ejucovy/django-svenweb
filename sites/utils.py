from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.decorators import wraps

def permalink(func):
    permalink_builder = getattr(settings, 'WIKI_PERMALINK_BUILDER', None)

    @wraps(func)
    def inner(instance, *args, **kwargs):
        bits = func(instance, *args, **kwargs)
        if permalink_builder is not None:
            bits = permalink_builder(instance, bits)
        return reverse(bits[0], None, *bits[1:3])
    return inner
