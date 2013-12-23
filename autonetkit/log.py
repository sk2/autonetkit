import logging
import logging.handlers
import autonetkit.config as config


ank_logger = logging.getLogger("ANK")
if not ank_logger.handlers:
    console_formatter = logging.Formatter("%(levelname)-1s %(message)s")
    ch = logging.StreamHandler()
    #ch.setLevel(logging.INFO)
    ch.setFormatter(console_formatter)
    ank_logger.addHandler(ch)

    file_logging = config.settings['Logging']['file']
    if file_logging:
        LOG_FILENAME =  "autonetkit.log"
        #fh = logging.FileHandler(LOG_FILENAME)
        LOG_SIZE = 2097152 # 2 MB
        fh = logging.handlers.RotatingFileHandler(
            LOG_FILENAME, maxBytes=LOG_SIZE, backupCount=5)
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s %(levelname)s "
            "%(funcName)s %(message)s")
        fh.setFormatter(formatter)
        ank_logger.addHandler(fh)

ank_logger.setLevel(logging.INFO)
# Reference for external access
logger = ank_logger
# Use approach of Pika, allows for autonetkit.log.debug("message")
debug = logger.debug
error = logger.error
info = logger.info
warning = logger.warning
exception = logger.exception
critical = logger.critical
