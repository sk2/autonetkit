from autonetkit.anm import NetworkModel as NetworkModel
from autonetkit.nidb import DeviceModel as DeviceModel

from autonetkit.ank_messaging import update_vis
# for legacy compatability
from autonetkit.ank_messaging import update_vis as update_http

from autonetkit.topologies.mixed import mixed as nm_mixed
from autonetkit.topologies.multi import multi as nm_multi
from autonetkit.topologies.house import house as nm_house