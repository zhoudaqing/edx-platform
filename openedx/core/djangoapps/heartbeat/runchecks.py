from importlib import import_module

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .defaults import HEARTBEAT_DEFAULT_CHECKS,\
    HEARTBEAT_EXTENDED_DEFAULT_CHECKS,\
    HEARTBEAT_CELERY_TIMEOUT


def runchecks(request):
    """
    Iterates through a tuple of systems checks,
    then returns a key name for the check and the value
    for that check.
    """
    response_dict = {}

    #Taken straight from Django
    #If there is a better way, I don't know it
    list_of_checks = getattr(settings, 'HEARTBEAT_CHECKS', HEARTBEAT_DEFAULT_CHECKS)
    if('extended' in request.GET):
        list_of_checks += getattr(settings, 'HEARTBEAT_EXTENDED_CHECKS', HEARTBEAT_EXTENDED_DEFAULT_CHECKS)

    for path in list_of_checks:
            i = path.rfind('.')
            module, attr = path[:i], path[i + 1:]
            try:
                if(module[0] == '.'):  # Relative path, assume relative to this app
                    mod = import_module(module, __package__)
                else:
                    mod = import_module(module)
                func = getattr(mod, attr)

                check_name, is_ok, message = func(request)
                response_dict[check_name] = {
                    'status': is_ok,
                    'message': message
                }
            except ImportError as e:
                raise ImproperlyConfigured('Error importing module %s: "%s"' % (module, e))
            except AttributeError:
                raise ImproperlyConfigured('Module "%s" does not define a "%s" callable' % (module, attr))

    return response_dict
