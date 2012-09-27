
# based on NetworkX exceptions

class AnkException(Exception):
    """Base class for AutoNetkit Exceptions"""

class AnkIncorrectFileFormat(AnkException):
    """Wrong file format"""

