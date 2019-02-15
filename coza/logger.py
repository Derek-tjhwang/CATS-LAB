import logging
import logging.config
from coza.config import LOG_LEVEL

FORMAT = '%(asctime)-15s [%(levelname)-5s] %(message)s'
LOG_CONFIG = {
        'version': 1,
        'formatters': {
            'default': {'format': FORMAT},
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'level': 'DEBUG'
            },
        },
        'root': {
            'handlers': ['console', ],
            'level': LOG_LEVEL
        }
}

logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger('root')

