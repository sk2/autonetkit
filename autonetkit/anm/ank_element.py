import logging
import autonetkit.log2
ank_logger_2 = logging.getLogger("ANK2")

class AnkElement(object):

    #TODO: put this into parent __init__?
    def init_logging(self, my_type):
        try:
            self_id = str(self)
        except Exception, e:
            #TODO: log warning here
            import autonetkit.log as log
            log.warning("Unable to set per-element logger %s", e)
            self_id = ""


        log_extra={"type": my_type, "id": self_id}
        object.__setattr__(self, 'log_extra', log_extra)

        #self.log_info = partial(ank_logger_2.info, extra=extra)
        #self.log_warning = partial(ank_logger_2.warning, extra=extra)
        #self.log_error = partial(ank_logger_2.error, extra=extra)
        #self.log_critical = partial(ank_logger_2.critical, extra=extra)
        #self.log_exception = partial(ank_logger_2.exception, extra=extra)
        #self.log_debug = partial(ank_logger_2.debug, extra=extra)

    def log_info(self, message):
        ank_logger_2.info(message, extra = self.log_extra)

    def log_warning(self, message):
        ank_logger_2.warning(message, extra = self.log_extra)

    def log_error(self, message):
        ank_logger_2.error(message, extra = self.log_extra)

    def log_critical(self, message):
        ank_logger_2.critical(message, extra = self.log_extra)

    def log_exception(self, message):
        ank_logger_2.exception(message, extra = self.log_extra)

    def log_debug(self, message):
        ank_logger_2.debug(message, extra = self.log_extra)


