import os

# ======================================
# Keys
KEY_COZA_HOST = 'COZA_HOST'
KEY_COZA_SECRET = 'COZA_SECRET'
KEY_LOG_LEVEL = 'LOG_LEVEL'

KEY_DEV_HOST = 'DEV_HOST'
KEY_DEV_SECRET = 'DEV_SECRET'

# ======================================
# Bot environment variables

env = os.environ
RUNNING_TYPE = 'DEV'
LOG_LEVEL = 'DEBUG'

COZA_HOST = None
COZA_SECRET = None

if RUNNING_TYPE == 'DEV':
    if KEY_DEV_HOST in env:
        COZA_HOST = env[KEY_DEV_HOST]

    if KEY_DEV_SECRET in env:
        COZA_SECRET = env[KEY_DEV_SECRET]


elif RUNNING_TYPE == 'SERVICE':
    if KEY_COZA_SECRET in env:
        COZA_SECRET = env[KEY_COZA_SECRET]

    if KEY_COZA_HOST in env:
        COZA_HOST = env[KEY_COZA_HOST]

if KEY_LOG_LEVEL in env:
    LOG_LEVEL = env[KEY_LOG_LEVEL]
