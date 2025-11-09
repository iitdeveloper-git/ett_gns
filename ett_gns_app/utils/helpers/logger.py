# ett_gns_app/utils/helpers/logger.py

import logging
import colorlog

def setup_logger():
    # Create a logger
    logger = colorlog.getLogger('my_logger')  # Use a specific logger name
    logger.setLevel(logging.INFO)  # Set the log level

    # Check if handlers are already set to avoid duplicates
    if not logger.handlers:
        # Create a console handler with color
        handler = colorlog.StreamHandler()
        handler.setLevel(logging.INFO)

        # Create a color formatter
        formatter = colorlog.ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(module)s - %(funcName)s  - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(handler)

    return logger
