import time
import autonetkit.diff

from autonetkit.nidb import NIDB

import autonetkit.verify
import autonetkit.push_changes


#TODO: write monitor that checks to see if latest file has changed in version directory
def main():
    nidb_versions_dir = "../versions/nidb/"
    nidb_a = NIDB()
#TODO: need to restore second latest, as may have changed tap ips since then
    previous_timestamp = 0
    while True:
        nidb_a.restore_latest(nidb_versions_dir)
        if nidb_a.timestamp == previous_timestamp:
            time.sleep(1)
        else:
            previous_timestamp = nidb_a.timestamp
            nidb_diffs = autonetkit.diff.nidb_diff(nidb_versions_dir)
            nidb_diff = nidb_diffs[0]

            print nidb_diff

            autonetkit.push_changes.apply_difference(nidb_a, nidb_diff)

def calculate_and_apply(nidb_a, nidb_b):
    diffs = autonetkit.diff.compare_nidb(nidb_a, nidb_b)
    print diffs

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
