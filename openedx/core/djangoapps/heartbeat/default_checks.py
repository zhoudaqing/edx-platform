from datetime import datetime, timedelta
from django.core.cache import cache
from django.db import connection
from django.db.utils import DatabaseError
from time import sleep, time
from xmodule.modulestore.django import modulestore
from xmodule.exceptions import HeartbeatFailure

from .tasks import sample_task


#DEFAULT SYSTEM CHECKS

#Modulestore

def check_modulestore():
    # This refactoring merely delegates to the default modulestore (which if it's mixed modulestore will
    # delegate to all configured modulestores) and a quick test of sql. A later refactoring may allow
    # any service to register itself as participating in the heartbeat. It's important that all implementation
    # do as little as possible but give a sound determination that they are ready.
    try:
        #@TODO Do we want to parse the output for split and mongo detail and return it?
        modulestore().heartbeat()
        return 'modulestore', True, "OK"
    except HeartbeatFailure as fail:
        return 'modulestore', False, unicode(fail)


def check_database():
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT CURRENT_DATE")
        cursor.fetchone()
        return 'sql', True, "OK"
    except DatabaseError as fail:
        return 'sql', False, unicode(fail)


#Caching
CACHE_KEY = 'heartbeat-test'
CACHE_VALUE = 'abc123'


def check_cache_set():
    try:
        cache.set(CACHE_KEY, CACHE_VALUE, 30)
        return 'cache_set', True, "OK"
    except fail:
        return 'cache_set', False, unicode(fail)


def check_cache_get():
    try:
        data = cache.get(CACHE_KEY)
        if data == CACHE_VALUE:
            return 'cache_get', True, "OK"
        else:
            return 'cache_get', False, "value check failed"
    except fail:
        return 'cache_get', False, unicode(fail)


#Celery
def check_celery():
    now = time()
    datetimenow = datetime.now()
    expires = datetimenow + timedelta(seconds=getattr(settings, 'HEARTBEAT_CELERY_TIMEOUT', HEARTBEAT_CELERY_TIMEOUT))

    try:
        task = sample_task.apply_async(expires=expires)
        while expires > datetime.now():
            if task.ready() and task.result:
                finished = str(time() - now)
                return 'celery', True, unicode({'time': finished})
            sleep(0.25)
        return 'celery', False, "expired"
    except Exception as fail:
        return 'celery', False, unicode(fail)
