import glob
import json
import time
import autonetkit.ank_messaging as ank_messaging
nodes = ["8"]

import autonetkit.anm
anm = autonetkit.anm.AbstractNetworkModel()
anm.restore_latest()
g_ipv4 = anm['ipv4']

for json_file in sorted(glob.glob('*.json')):
    with open(json_file, "r") as fh:
        data = json.loads(fh.read())
    print data

    if not len(data):
        continue

    processed = []
    for line in data:
        processed.append([g_ipv4.node(n) for n in line])

    autonetkit.update_http(anm)
    ank_messaging.highlight(nodes, [], processed)

    raw_input("Press Enter to continue...")
    
