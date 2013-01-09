import logging
import autonetkit.config as config

#colors based on http://stackoverflow.com/questions/384076

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

#The background is set with 40 plus the number of the color, and the foreground with 30

#These are the sequences need to get colored ouput
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"

def formatter_message(message, use_color = True):
    if use_color:
        message = message.replace("$RESET", RESET_SEQ).replace("$BOLD", BOLD_SEQ)
    else:
        message = message.replace("$RESET", "").replace("$BOLD", "")
    return message

COLORS = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': YELLOW,
    'ERROR': RED
}

class ColoredFormatter(logging.Formatter):
    def __init__(self, msg, use_color = True):
        logging.Formatter.__init__(self, msg)
        self.use_color = use_color

    def format(self, record):
        levelname = record.levelname
        if self.use_color and levelname in COLORS:
            levelname_color = COLOR_SEQ % (30 + COLORS[levelname]) + levelname + RESET_SEQ
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)


    # Custom logger class with multiple destinations
class ColoredLogger(logging.Logger):
    FORMAT = "%(levelname)-1s %(message)s"
    COLOR_FORMAT = formatter_message(FORMAT, True)
    def __init__(self, name):
        logging.Logger.__init__(self, name, logging.WARNING)

        color_formatter = ColoredFormatter(self.COLOR_FORMAT)

        console = logging.StreamHandler()
        console.setFormatter(color_formatter)

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


logging.setLoggerClass(ColoredLogger)
logger = logging.getLogger("ANK")
logger.setLevel(logging.INFO)

# Use approach of Pika, allows for autonetkit.log.debug("message")
debug = logger.debug
error = logger.error
info = logger.info
warning = logger.warning

