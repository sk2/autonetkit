from autonetkit.packager.base import AbstractPlatformPackager
from autonetkit.packager.kathara import KatharaPlatformPackager


def get_platform_builder(target: str) -> AbstractPlatformPackager:
    """

    @param target:
    @return:
    """
    map = {
        "kathara": KatharaPlatformPackager()
    }

    return map[target]
