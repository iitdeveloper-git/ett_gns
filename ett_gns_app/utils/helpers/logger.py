# ett_gns_app/utils/helpers/logger.py

import logging
import colorlog


def setup_logger():
    # Only configure formatters and handlers for the root logger
    logger = colorlog.getLogger()
    if not getattr(logger, "is_setup_done", False):
        logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        handler = colorlog.StreamHandler()
        handler.setLevel(logging.INFO)

        formatter = colorlog.ColoredFormatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s  - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Avoid running setup multiple times
        logger.is_setup_done = True

    return logger
