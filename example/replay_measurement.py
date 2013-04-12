import glob
import json
import time
import autonetkit.ank_messaging as ank_messaging
nodes = ["8"]

import autonetkit.verify

import autonetkit.anm
anm = autonetkit.anm.AbstractNetworkModel()
anm.restore("measurement_sh_ip_route/anm_20130409_200932.json.gz")
g_ipv4 = anm['ipv4']

for json_file in sorted(glob.glob('measurement_sh_ip_route/*.json')):
    with open(json_file, "r") as fh:
        data = json.loads(fh.read())
    #print data

    if not len(data):
        continue

    processed = []
    for line in data:
        processed.append([g_ipv4.node(n) for n in line])

    verification_results = autonetkit.verify.igp_routes(anm, processed)
    processed_with_results = []
    for line in processed:
        prefix = str(line[-1].subnet)
        result = verification_results[prefix]
        processed_with_results.append({
            'path': line,
            'verified': result,
            })

    autonetkit.update_http(anm)
    ank_messaging.highlight(nodes, [], processed_with_results)

    raw_input("Press Enter to continue...")
    
