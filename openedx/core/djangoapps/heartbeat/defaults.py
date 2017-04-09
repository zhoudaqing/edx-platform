HEARTBEAT_DEFAULT_CHECKS = [
    '.default_checks.check_modulestore',
    '.default_checks.check_database',
]

HEARTBEAT_EXTENDED_DEFAULT_CHECKS = (
    '.default_checks.check_celery',
)

HEARTBEAT_CELERY_TIMEOUT = 5
