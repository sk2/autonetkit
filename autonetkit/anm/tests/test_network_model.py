from autonetkit.topologies import house
from autonetkit.anm.network_model import NetworkModel
from mock import patch

def test_init():
    anm = NetworkModel()
    print anm


def test_len():
    anm = NetworkModel()
    """ default overlays are:
    input, phy, _dependencies, graphics
    """
    assert(len(anm) == 4)
    anm.add_overlay("test")
    assert(len(anm) == 5)

def test_init():
    anm = NetworkModel()
    assert(anm.has_overlay(("phy")) is True)
    assert(anm.has_overlay(("test")) is False)
