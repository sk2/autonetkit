import logging
import autonetkit.config as config



class ConsoleLogger(logging.Logger):
    #TODO: set color based on terminal type
    def __init__(self, name):
        console_formatter = logging.Formatter("%(levelname)-1s %(message)s")
        logging.Logger.__init__(self, name, logging.WARNING)
        console = logging.StreamHandler()
        console.setFormatter(console_formatter)

        self.addHandler(console)
        return

import logging.handlers
file_logging = config.settings['Logging']['file']
if file_logging:
    LOG_FILENAME =  "autonetkit.log"
    LOG_SIZE = 2097152 # 2 MB
    fh = logging.handlers.RotatingFileHandler(
                LOG_FILENAME, maxBytes=LOG_SIZE, backupCount=5)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)s "
                                "%(funcName)s %(message)s")
    fh.setFormatter(formatter)

    logging.getLogger('').addHandler(fh)


logging.setLoggerClass(ConsoleLogger)
logger = logging.getLogger("ANK")
logger.setLevel(logging.INFO)

# Use approach of Pika, allows for autonetkit.log.debug("message")
debug = logger.debug
error = logger.error
info = logger.info
warning = logger.warning

