class AutoNetkitException(Exception):

    """Base class for AutoNetkit Exceptions"""


class AnkIncorrectFileFormat(AutoNetkitException):

    """Wrong file format"""


class OverlayNotFound(AutoNetkitException):

    def __init__(self, errors):
        self.Errors = errors

    def __str__(self):
        return 'Overlay %s not found' % self.Errors
