import glob
import json
import time
import random
import autonetkit.ank_messaging as ank_messaging

import autonetkit.anm
anm = autonetkit.anm.AbstractNetworkModel()
anm.restore("measurement_sh_ip_route/anm_20130409_200932.json.gz")
g_ipv4 = anm['ipv4']
g_ospf = anm['ospf']


while True:

    path = []
    for x in range(3):
        path.append(random.sample(list(g_ospf.nodes()), 3))

    print path
    #path = [n for n in path]
    processed = path
    nodes = [path[0][0]]
    print nodes, processed
    #processed = []
    #processed = [[g_ipv4.node("8"), g_ipv4.node("4"), g_ipv4.node("1")]]

    autonetkit.update_http(anm)
    ank_messaging.highlight(nodes, [], processed)

    time.sleep(3)
    

