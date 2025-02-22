import logging.config

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(asctime)s - %(levelname)s - %(message)s"
        },
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "ascii-video-server": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False
        }
    },
})
log = logging.getLogger("ascii-video-server")
