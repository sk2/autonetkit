import logging
import logging.handlers
import autonetkit.config as config

ank_logger = logging.getLogger("ANK2")
if not ank_logger.handlers:
    console_formatter = logging.Formatter("%(levelname)-1s %(type)s %(id)s %(message)s")
    ch = logging.StreamHandler()
    #ch.setLevel(logging.INFO)
    ch.setFormatter(console_formatter)
    ch.setLevel(logging.INFO)
    ank_logger.addHandler(ch)



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
