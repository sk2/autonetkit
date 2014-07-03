Changelog
=========

Testing release
---------------

- Merge pull request #242 from sk2/ACLs. [Simon Knight]

  Ac ls

- Add tox. [Simon Knight]

- Merge pull request #241 from sk2/ACLs. [Simon Knight]

  Ac ls

v0.9.2 (2014-06-27)
-------------------

Changes
~~~~~~~

- >= rather than == for deps. [Simon Knight]

- Update info on ip blocks. [Simon Knight]

v0.9.1 (2014-05-13)
-------------------

New
~~~

- User: record overlay dependencies to new overlay. [Simon Knight]

Changes
~~~~~~~

- Minor tweaks. [Simon Knight]

- Condense example. [Simon Knight]

- Tidy. [Simon Knight]

- Tidy. [Simon Knight]

- Update docs for json example. [Simon Knight]

- Add Json to doc for gh-222. [Simon Knight]

- User: Initial commit of JSON load code for gh-222. [Simon Knight]

  Example in tests/house.json if using dev build of ank:  ``` $
  autonetkit -f tests/house.json INFO VIRL Configuration Engine 0.9.0
  INFO AutoNetkit 0.9.0 INFO IPv4 allocations: Infrastructure:
  10.0.0.0/8, Loopback: 192.168.0.0/22 INFO Allocating v4 Infrastructure
  IPs INFO Allocating v4 Primary Host loopback IPs INFO Topology not
  created for VIRL, skipping Cisco PCE design rules INFO Skipping iBGP
  for iBGP disabled nodes: [] INFO All validation tests passed. INFO
  Rendering Configuration Files INFO Finished ```  if run in monitor
  mode, then changes will be reflected live: ``` $ ank_webserver ```
  and then ``` $ autonetkit -f tests/house.json —monitor ```

- Updates. [Simon Knight]

- Rebuild doc. [Simon Knight]

- Increment year. [Simon Knight]

- Run sphinx-apidoc. [Simon Knight]

- Adding doctests. [Simon Knight]

- User: update_http -> update_vis. [Simon Knight]

- User: Initial support for multi-homed servers for VIRL-425. [Simon
  Knight]

- Add initial support to auto-build dependency diagrams. [Simon Knight]

Other
~~~~~

- Merge pull request #237 from oliviertilmans/patch-1. [Simon Knight]

  The network might not run BGP

- The network might not run BGP. [oliviertilmans]

  This result in a Key Error

- Merge pull request #236 from sk2/parallel. [Simon Knight]

  Parallel

- Merge pull request #235 from sk2/ACLs. [Simon Knight]

  Ac ls

- Revert "chg: dev: add ACL placeholder for gh-234" [Simon Knight]

  This reverts commit 4941b893daf279e5bb24a0b54c10ed490db27716.

- Merge pull request #232 from sk2/render2.0. [Simon Knight]

  Render2.0

- Add: dev: initial work to support vlans for gh-229. [Simon Knight]

- Update README.md. [Simon Knight]

- Merge pull request #228 from sk2/parallel. [Simon Knight]

  chg: doc: minor tweaks

- Merge pull request #227 from sk2/parallel. [Simon Knight]

  Parallel

- Update README.md. [Simon Knight]

- Update README.md. [Simon Knight]

- Merge pull request #226 from sk2/parallel. [Simon Knight]

  Chg: doc: add Json to doc for gh-222

- Merge pull request #225 from sk2/parallel. [Simon Knight]

  Chg: User: Initial commit of JSON load code for gh-222

- Merge pull request #224 from sk2/parallel. [Simon Knight]

  Parallel

- Merge pull request #223 from sk2/parallel. [Simon Knight]

  Parallel

- Merge pull request #221 from sk2/parallel. [Simon Knight]

  Parallel

v0.9.0 (2014-03-24)
-------------------

New
~~~

- User: Support layer2 and layer3 overlays for gh-206. [Simon Knight]

Changes
~~~~~~~

- User: Sort nodes before allocation, closes gh-208. [Simon Knight]

- User: label-based sort if present closes gh-207. [Simon Knight]

- User: add ability to search for interfaces by their "id" string e.g.
  "GigabitEthernet0/1" [Simon Knight]

v0.8.39 (2014-03-14)
--------------------

Changes
~~~~~~~

- User: Allow custom config injection for VIRL-122. [Simon Knight]

v0.8.38 (2014-03-13)
--------------------

Changes
~~~~~~~

- User: Handle IP addresses on L3 devices for VIRL-372. [Simon Knight]

- User: support custom unsupported server templates for VIRL-378. [Simon
  Knight]

- User: add "external_connector" device_type for VIRL-672. [Simon
  Knight]

- User: only validate IP on Layer 3 devices for VIRL-672. [Simon Knight]

- Allow specifying edge properties (color/width) [Simon Knight]

v0.8.37 (2014-03-11)
--------------------

Fix
~~~

- User: Corrects bug with non-routers in EIGRP fixes VIRL-659. [Simon
  Knight]

  Had extra ISIS NET address line

v0.8.35 (2014-03-10)
--------------------

Changes
~~~~~~~

- Update warnings to not warn if no subnet/prefix set. [Simon Knight]

v0.8.33 (2014-03-05)
--------------------

Changes
~~~~~~~

- User: Use ASN as process-id for IGP for VIRL-602. [Simon Knight]

  Causes problems if multiple ASes connected across a multi-point
  network.

Other
~~~~~

- Add overview video. [Simon Knight]

v0.8.32 (2014-02-14)
--------------------

New
~~~

- User: Allow manually specified IPv6 blocks for VIRL-481. [Simon
  Knight]

Changes
~~~~~~~

- User: Config driven IP defaults, better logging of problems with
  manually specified IPs. [Simon Knight]

- User: Swap default IPv6 blocks for infra/loopback to be sequential.
  [Simon Knight]

v0.8.31 (2014-02-14)
--------------------

Changes
~~~~~~~

- User: Tidied up VRF role notification logic to aggregate by role.
  VIRL-368. [Simon Knight]

- User: Exclude BGP block if no iBGP/eBGP sessions. VIRL-564. [Simon
  Knight]

v0.8.29 (2014-02-14)
--------------------

New
~~~

- User: Warn that IPv6 MPLS VPNs not currently supported for VIRL-56.
  [Simon Knight]

Changes
~~~~~~~

- User: update iBGP design rules for VIRL-558. [Simon Knight]

Fix
~~~

- User: Allow PE RRC nodes to participate in ibgp_vpn_v4. [Simon Knight]

v0.8.26 (2014-02-13)
--------------------

Changes
~~~~~~~

- User: Add ibgp "peer" type for VIRL-558. [Simon Knight]

- User: Clarify IPv4 allocation warning message for VIRL-550. [Simon
  Knight]

- User: list Interfaces as GigabitEthernet0/1.RR_2 instead of
  (GigabitEthernet0/1, RR_2) [Simon Knight]

v0.8.17 (2014-01-31)
--------------------

New
~~~

- User: Allow user-defined IPv6 IPs (infra + loopback) [Simon Knight]

Changes
~~~~~~~

- User: More descriptive logs for user-defined IPv6 addresses. [Simon
  Knight]

Fix
~~~

- User: Bugfix for EIGRP IPv6 for VIRL-493. [Simon Knight]

v0.8.14 (2014-01-24)
--------------------

New
~~~

- User: Warn if partial IPs set for VIRL-456. [Simon Knight]

- User: Display human-readable ibgp_role for VIRL-469. [Simon Knight]

v0.8.12 (2014-01-22)
--------------------

Changes
~~~~~~~

- User: Update logging. [Simon Knight]

v0.8.11 (2014-01-22)
--------------------

Changes
~~~~~~~

- User: Tidy logging. [Simon Knight]

- User: Warn for unsupported device features. [Simon Knight]

- User: Use VIRL platform identifier instead of Cisco. [Simon Knight]

- User: Tidy logging messages. [Simon Knight]

v0.8.10 (2014-01-21)
--------------------

Fix
~~~

- Sort values neigh_most_frequent so tie-break chooses lowest. [Simon
  Knight]

  Addresses issue with stability in IP addressing: inter-asn links had a
  collision domain that was arbitrarily being allocated to one or the
  other ASN depending on the arbitarty position. This ensures the lowest
  is always returned in a tie-break leading to repeatable addressing
  (especially important for automated tests)

v0.8.9 (2014-01-20)
-------------------

- Merge branch 'master' of github.com:sk2/autonetkit. [Simon Knight]

  Conflicts:         .bumpversion.cfg         autonetkit/render.py
  setup.py

- Merge cleanup. [Simon Knight]

v0.8.7 (2014-01-20)
-------------------

- @chg: dev: renaming. [Simon Knight]

- @chg: dev: renaming. [Simon Knight]

v0.8.6 (2014-01-20)
-------------------

New
~~~

- User: Display address blocks to use for VIRL-350. [Simon Knight]

- User: Display address blocks to use for VIRL-350. [Simon Knight]

v0.8.4 (2014-01-16)
-------------------

New
~~~

- User: add per-element logging for GH-190. [Simon Knight]

- User: add per-element logging for GH-190. [Simon Knight]

- User: add single config for gh-189. [Simon Knight]

- User: add single config for gh-189. [Simon Knight]

- User: Screenshot capture for GH-188. [Simon Knight]

- User: Screenshot capture for GH-188. [Simon Knight]

Other
~~~~~

- Change: dev: remove superseded config. [Simon Knight]

- Change: dev: remove superseded config. [Simon Knight]

- Change: dev: refactor XR OSPF by interfaces to common router_base.
  [Simon Knight]

- Change: dev: refactor XR OSPF by interfaces to common router_base.
  [Simon Knight]

- Update changelog. [Simon Knight]

- Update changelog. [Simon Knight]

v0.8.3 (2014-01-13)
-------------------

- Add gitchangelog support. [sk2]

- Add gitchangelog support. [sk2]

- Move indent correctly inside loop. [sk2]

- Move indent correctly inside loop. [sk2]

- Typo fix for ebgp not ibgp. [sk2]

- Typo fix for ebgp not ibgp. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Add read me. [sk2]

- Add read me. [sk2]

- Update. [sk2]

- Update. [sk2]

- Add img. [sk2]

- Add img. [sk2]

- Examples. [sk2]

- Examples. [sk2]

- Add cwd to templates search dir. [sk2]

- Add cwd to templates search dir. [sk2]

- Add ordering. [sk2]

- Add ordering. [sk2]

- Add note. [sk2]

- Add note. [sk2]

- Support v6 bgp. [sk2]

- Support v6 bgp. [sk2]

- Add note. [sk2]

- Add note. [sk2]

- Add __ne__ and ordering. [sk2]

- Add __ne__ and ordering. [sk2]

- Support nidb nodes. [sk2]

- Support nidb nodes. [sk2]

- Add example. [sk2]

- Add example. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Handle new overlays. [sk2]

- Handle new overlays. [sk2]

- New overlay. [sk2]

- New overlay. [sk2]

- Better json. [sk2]

- Better json. [sk2]

- Tutorial notebook. [sk2]

- Tutorial notebook. [sk2]

- Add new test case notes. [sk2]

- Add new test case notes. [sk2]

- Better debugging for templates. [sk2]

- Better debugging for templates. [sk2]

- More support for gh-186. [sk2]

- More support for gh-186. [sk2]

- Move mpls code to separate module. [sk2]

- Move mpls code to separate module. [sk2]

- More support for gh-186. [sk2]

- More support for gh-186. [sk2]

- Pep8. [sk2]

- Pep8. [sk2]

- Improvements to setting defaults on bunches. [sk2]

- Improvements to setting defaults on bunches. [sk2]

- Remove old demos. [sk2]

- Remove old demos. [sk2]

- Add config_stanza class for gh-186. [sk2]

- Add config_stanza class for gh-186. [sk2]

- Add option for stack_trace (useful for dev) [sk2]

- Add option for stack_trace (useful for dev) [sk2]

- Add browser test. [sk2]

- Add browser test. [sk2]

- Connectors. [sk2]

- Connectors. [sk2]

v0.8.2 (2014-01-10)
-------------------

- Remove old call to publish data. [sk2]

- Remove old call to publish data. [sk2]

v0.8.1 (2014-01-10)
-------------------

- Add note. [sk2]

- Add note. [sk2]

- Remove unused messaging functions. [sk2]

- Remove unused messaging functions. [sk2]

- Add log message. [sk2]

- Add log message. [sk2]

- Update anm tests. [sk2]

- Update anm tests. [sk2]

- Testing for anm. [sk2]

- Testing for anm. [sk2]

- Remove directed. [sk2]

- Remove directed. [sk2]

- Improving edge-case handling. [sk2]

- Improving edge-case handling. [sk2]

- Remove state for pickling - use json. [sk2]

- Remove state for pickling - use json. [sk2]

- Improving handling for custom overlays. [sk2]

- Improving handling for custom overlays. [sk2]

- Remove unused code. [sk2]

- Remove unused code. [sk2]

v0.8.0 (2014-01-08)
-------------------

- Remove old ibgp code. [sk2]

- Remove old ibgp code. [sk2]

- More removal of edge_id for gh-184. [sk2]

- More removal of edge_id for gh-184. [sk2]

- Closes gh-184. [sk2]

- Closes gh-184. [sk2]

- Pylint. [sk2]

- Pylint. [sk2]

v0.7.33 (2014-01-08)
--------------------

- Update warnings. [sk2]

- Update warnings. [sk2]

v0.7.32 (2014-01-08)
--------------------

- Add other AS subnets. [sk2]

- Add other AS subnets. [sk2]

v0.7.31 (2014-01-07)
--------------------

- Tidy. [sk2]

- Tidy. [sk2]

- Handle non-subnet collision domains (i.e. no nodes) [sk2]

- Handle non-subnet collision domains (i.e. no nodes) [sk2]

- Rename subtype. [sk2]

- Rename subtype. [sk2]

- Pass exception up. [sk2]

- Pass exception up. [sk2]

v0.7.29 (2014-01-06)
--------------------

- Use official subtypes. [sk2]

- Use official subtypes. [sk2]

v0.7.27 (2014-01-04)
--------------------

- Pep8. [sk2]

- Pep8. [sk2]

v0.7.26 (2014-01-03)
--------------------

- Add logging. [sk2]

- Add logging. [sk2]

v0.7.25 (2014-01-03)
--------------------

- Fix issue with uuids being re-used but discarded, update logging.
  [sk2]

- Fix issue with uuids being re-used but discarded, update logging.
  [sk2]

v0.7.24 (2014-01-02)
--------------------

- Catching overlay uuid deletion errors. [sk2]

- Catching overlay uuid deletion errors. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Handling of interfaces in adding edges. [sk2]

- Handling of interfaces in adding edges. [sk2]

- Allow uuid to be specified in call. [sk2]

- Allow uuid to be specified in call. [sk2]

- Update connectors. [sk2]

- Update connectors. [sk2]

- Add comment. [sk2]

- Add comment. [sk2]

- Add script to build wheel. [sk2]

- Add script to build wheel. [sk2]

- Isort imports. [sk2]

- Isort imports. [sk2]

v0.7.23 (2013-12-27)
--------------------

- Enable telnet and ssh over vty. [sk2]

- Enable telnet and ssh over vty. [sk2]

- Tidying. [sk2]

- Tidying. [sk2]

v0.7.20 (2013-12-23)
--------------------

- Correct bug in writing static instead of host routes. [sk2]

- Correct bug in writing static instead of host routes. [sk2]

v0.7.19 (2013-12-23)
--------------------

- Tidy. [sk2]

- Tidy. [sk2]

v0.7.17 (2013-12-23)
--------------------

- Tidy. [sk2]

- Tidy. [sk2]

- Tidy logging. [sk2]

- Tidy logging. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Add test. [sk2]

- Add test. [sk2]

- Add tests. [sk2]

- Add tests. [sk2]

- Add test. [sk2]

- Add test. [sk2]

- Add test. [sk2]

- Add test. [sk2]

- Add test. [sk2]

- Add test. [sk2]

- Add test topology. [sk2]

- Add test topology. [sk2]

v0.7.16 (2013-12-20)
--------------------

- Add extra onepk line. [sk2]

- Add extra onepk line. [sk2]

v0.7.15 (2013-12-20)
--------------------

- Tidy. [sk2]

- Tidy. [sk2]

v0.7.14 (2013-12-20)
--------------------

- Return the node label rendered rather than node_id for repr of
  interfaces. [sk2]

- Return the node label rendered rather than node_id for repr of
  interfaces. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

v0.7.13 (2013-12-19)
--------------------

- If exception, send the visualisation that was constructed to help
  debug. [sk2]

- If exception, send the visualisation that was constructed to help
  debug. [sk2]

- Return nonzero if error. [sk2]

- Return nonzero if error. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Add top-level exception capturing. [sk2]

- Add top-level exception capturing. [sk2]

v0.7.12 (2013-12-19)
--------------------

- Revert out. [sk2]

- Revert out. [sk2]

- Onepk syntax change. [sk2]

- Onepk syntax change. [sk2]

- Remove todo. [sk2]

- Remove todo. [sk2]

- More descriptive error message for mismatched subnets. [sk2]

- More descriptive error message for mismatched subnets. [sk2]

v0.7.10 (2013-12-18)
--------------------

- Copy label across to ipv4 and v6 graphs for display. [sk2]

- Copy label across to ipv4 and v6 graphs for display. [sk2]

v0.7.9 (2013-12-18)
-------------------

- Add yaml helpers for multiline strings. [sk2]

- Add yaml helpers for multiline strings. [sk2]

- Default handler. [sk2]

- Default handler. [sk2]

- Add validate catch. [sk2]

- Add validate catch. [sk2]

- Handle no routing. [sk2]

- Handle no routing. [sk2]

v0.7.8 (2013-12-12)
-------------------

- Closes gh-183. [sk2]

- Closes gh-183. [sk2]

- Use new vars, tidy. [sk2]

- Use new vars, tidy. [sk2]

- Info -> debug. [sk2]

- Info -> debug. [sk2]

- Lists instead of generators. [sk2]

- Lists instead of generators. [sk2]

- Ignores. [sk2]

- Ignores. [sk2]

- Merge pull request #182 from iainwp/master. [Simon Knight]

  modification to accept a configuration file from an environment
  variable

- Merge pull request #182 from iainwp/master. [Simon Knight]

  modification to accept a configuration file from an environment
  variable

- Comment out custom code. [sk2]

- Comment out custom code. [sk2]

- Revert labels. [sk2]

- Revert labels. [sk2]

- 254 on static route. [sk2]

- 254 on static route. [sk2]

- Modification to accept a configuration file from an environment
  variable. [iainwp]

- Modification to accept a configuration file from an environment
  variable. [iainwp]

- Merge pull request #125 from oliviertilmans/loopback_ids. [Simon
  Knight]

  Loopback interface needs to have an associated id with them

- Merge pull request #125 from oliviertilmans/loopback_ids. [Simon
  Knight]

  Loopback interface needs to have an associated id with them

v0.7.4 (2013-12-02)
-------------------

- Tidy overlay names. [sk2]

- Tidy overlay names. [sk2]

- Handle vis corner case if just input. [sk2]

- Handle vis corner case if just input. [sk2]

v0.7.3 (2013-11-29)
-------------------

- Correct version that bumpversion clobbered. [sk2]

- Correct version that bumpversion clobbered. [sk2]

- Add helper function to return neighbors of an interface. [sk2]

- Add helper function to return neighbors of an interface. [sk2]

- Add is_bound property for nidb interfaces for parity with anm. [sk2]

- Add is_bound property for nidb interfaces for parity with anm. [sk2]

- Set mgmt interface name correctly. [sk2]

- Set mgmt interface name correctly. [sk2]

- Remove extra http postings. [sk2]

- Remove extra http postings. [sk2]

- Add helper function to return neighbors of an interface. [sk2]

- Add helper function to return neighbors of an interface. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

v0.7.2 (2013-11-27)
-------------------

- Tidy. [sk2]

- Tidy. [sk2]

- Tidying version string. [sk2]

- Tidying version string. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Fix extra syntax. [sk2]

- Fix extra syntax. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

v0.7.1 (2013-11-26)
-------------------

- More work for cloud-init support. [sk2]

- More work for cloud-init support. [sk2]

- Ignore .yaml. [sk2]

- Ignore .yaml. [sk2]

- Improving render for cloud init output. [sk2]

- Improving render for cloud init output. [sk2]

- Cloud init. [sk2]

- Cloud init. [sk2]

- Move out vis. [sk2]

- Move out vis. [sk2]

- Top-level behaviour. [sk2]

- Top-level behaviour. [sk2]

- Change top level peering behaviour. [sk2]

- Change top level peering behaviour. [sk2]

- Lock deps. [sk2]

- Lock deps. [sk2]

- Tidying. [sk2]

- Tidying. [sk2]

v0.6.8 (2013-11-19)
-------------------

- First iteration of simplified RR/HRR iBGP. [sk2]

- First iteration of simplified RR/HRR iBGP. [sk2]

- Refactor out ibgp. [sk2]

- Refactor out ibgp. [sk2]

- Remove extra node. [sk2]

- Remove extra node. [sk2]

- Path colours. [sk2]

- Path colours. [sk2]

- Handle base topo. [sk2]

- Handle base topo. [sk2]

- Update colours. [sk2]

- Update colours. [sk2]

- Error handling. [sk2]

- Error handling. [sk2]

- Logging. [sk2]

- Logging. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Basic ibgp check. [sk2]

- Basic ibgp check. [sk2]

v0.6.7 (2013-10-30)
-------------------

- Fix looping issue not assigning server ips. [sk2]

- Fix looping issue not assigning server ips. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

v0.6.6 (2013-10-29)
-------------------

- Write IPs onto all server interfaces. [sk2]

- Write IPs onto all server interfaces. [sk2]

v0.6.5 (2013-10-28)
-------------------

- Redo bgp peering for ios. [sk2]

- Redo bgp peering for ios. [sk2]

- Revisiting bgp peering. [sk2]

- Revisiting bgp peering. [sk2]

- Adding nailed up routes for eBGP. [sk2]

- Adding nailed up routes for eBGP. [sk2]

v0.6.4 (2013-10-22)
-------------------

- Use -host for /32. [sk2]

- Use -host for /32. [sk2]

v0.6.3 (2013-10-22)
-------------------

- Tidying. [sk2]

- Tidying. [sk2]

- Add config-driven webserver port. [sk2]

- Add config-driven webserver port. [sk2]

v0.6.2 (2013-10-21)
-------------------

- Fix server issue. [sk2]

- Fix server issue. [sk2]

v0.6.1 (2013-10-18)
-------------------

- Toggle routing config. [sk2]

- Toggle routing config. [sk2]

v0.6.0 (2013-10-18)
-------------------

- Add mpls oam. [sk2]

- Add mpls oam. [sk2]

- Call mpls oam module. [sk2]

- Call mpls oam module. [sk2]

- Add mpls oam. [sk2]

- Add mpls oam. [sk2]

- Don't auto-correct explicitly set ASNs. [sk2]

- Don't auto-correct explicitly set ASNs. [sk2]

- Fix typo in comment. [sk2]

- Fix typo in comment. [sk2]

- Exclude multipoint edges from mpls te and rsvp. [sk2]

- Exclude multipoint edges from mpls te and rsvp. [sk2]

- Mark multipoint edges. [sk2]

- Mark multipoint edges. [sk2]

- Fallback to category20b colours if > 10 groups. [sk2]

- Fallback to category20b colours if > 10 groups. [sk2]

- Restore cef for ios. [sk2]

- Restore cef for ios. [sk2]

- Update doc. [sk2]

- Update doc. [sk2]

- Interface handling if specified name for servers. [sk2]

- Interface handling if specified name for servers. [sk2]

- Add lo routes. [sk2]

- Add lo routes. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Remove debug, tidy. [sk2]

- Remove debug, tidy. [sk2]

- Include linux in manifest. [sk2]

- Include linux in manifest. [sk2]

- Add linux static routes. [sk2]

- Add linux static routes. [sk2]

- Add mpls te rules. [sk2]

- Add mpls te rules. [sk2]

- Ubuntu server class for static routes. [sk2]

- Ubuntu server class for static routes. [sk2]

- Server base class. [sk2]

- Server base class. [sk2]

- Base device class. [sk2]

- Base device class. [sk2]

- Tidying, add mpls to ios. [sk2]

- Tidying, add mpls to ios. [sk2]

- Fix ebgp session created on switch that has both ebgp and ibgp
  sessions. [sk2]

- Fix ebgp session created on switch that has both ebgp and ibgp
  sessions. [sk2]

- Adding route config rendering. [sk2]

- Adding route config rendering. [sk2]

- Tidying oo. [sk2]

- Tidying oo. [sk2]

- Add mpls code. [sk2]

- Add mpls code. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Add fn to check server asn. [sk2]

- Add fn to check server asn. [sk2]

- Add mpls callout. [sk2]

- Add mpls callout. [sk2]

- Update asn setting. [sk2]

- Update asn setting. [sk2]

- Update asn handling: copy from phy if present. [sk2]

- Update asn handling: copy from phy if present. [sk2]

v0.5.21 (2013-09-06)
--------------------

- Set ipv4 and routing enabled defaults. [sk2]

- Set ipv4 and routing enabled defaults. [sk2]

- Post-collect processing. [sk2]

- Post-collect processing. [sk2]

- Remove uuid from test. [sk2]

- Remove uuid from test. [sk2]

- Reverse map for single ip. [sk2]

- Reverse map for single ip. [sk2]

- Multi-user uuid support. [sk2]

- Multi-user uuid support. [sk2]

v0.5.20 (2013-08-29)
--------------------

- Tidying, adding in vrfs. [sk2]

- Tidying, adding in vrfs. [sk2]

v0.5.19 (2013-08-28)
--------------------

- More collect. [sk2]

- More collect. [sk2]

v0.5.18 (2013-08-27)
--------------------

- Rename collect server. [sk2]

- Rename collect server. [sk2]

- Z ordering. [sk2]

- Z ordering. [sk2]

- Node data mapping. [sk2]

- Node data mapping. [sk2]

- Inc default threads to 5. [sk2]

- Inc default threads to 5. [sk2]

- Remove interfaces from node data dump. [sk2]

- Remove interfaces from node data dump. [sk2]

- Reverse mapping ips. [sk2]

- Reverse mapping ips. [sk2]

- Pep8. [sk2]

- Pep8. [sk2]

v0.5.17 (2013-08-23)
--------------------

- Allow no ip allocs. [sk2]

- Allow no ip allocs. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Allow no ip allocs. [sk2]

- Allow no ip allocs. [sk2]

- Split out functions from build_network. [sk2]

- Split out functions from build_network. [sk2]

- Allow no ip allocs. [sk2]

- Allow no ip allocs. [sk2]

- Allow no ip allocs. [sk2]

- Allow no ip allocs. [sk2]

v0.5.16 (2013-08-22)
--------------------

- Move endif to end of bgp block to enable bgp to be disabled. [sk2]

- Move endif to end of bgp block to enable bgp to be disabled. [sk2]

- Add todo. [sk2]

- Add todo. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Option to disable routing protocols. [sk2]

- Option to disable routing protocols. [sk2]

- Nonzero function. [sk2]

- Nonzero function. [sk2]

- Include eigrp overlay. [sk2]

- Include eigrp overlay. [sk2]

v0.5.14 (2013-08-22)
--------------------

- Remvoe debug. [sk2]

- Remvoe debug. [sk2]

v0.5.13 (2013-08-22)
--------------------

- Only require specified ip for bound interfaces. [sk2]

- Only require specified ip for bound interfaces. [sk2]

v0.5.12 (2013-08-21)
--------------------

- Updates. [sk2]

- Updates. [sk2]

- Add lo to eigrp v6. [sk2]

- Add lo to eigrp v6. [sk2]

- Try seperate packages if possible. [sk2]

- Try seperate packages if possible. [sk2]

- Add eigrp. [sk2]

- Add eigrp. [sk2]

v0.5.9 (2013-08-16)
-------------------

- Remove debug. [sk2]

- Remove debug. [sk2]

v0.5.8 (2013-08-16)
-------------------

- Update. [sk2]

- Update. [sk2]

v0.5.7 (2013-08-13)
-------------------

- Misc bugfixes. [sk2]

- Latest. [sk2]

- Tidy. [sk2]

- Measure updates. [sk2]

- More collection. [sk2]

- Measurement -> collection. [sk2]

- More measure. [sk2]

- Update docs. [sk2]

- Remove unused measuremetn. [sk2]

- Measure. [sk2]

v0.5.6 (2013-08-02)
-------------------

- More measure. [sk2]

v0.5.5 (2013-08-02)
-------------------

- Add colorbrewer. [sk2]

- Add colorbrewer. [sk2]

- Tidying colours. [sk2]

- Tidying colours. [sk2]

- Add enable secret. [sk2]

- Measurement improvements. [sk2]

- Tidy. [sk2]

- Reorganise, ultra -> csr1000v, add hash. [sk2]

- Tidy. [sk2]

- Add server. [sk2]

v0.5.4 (2013-08-01)
-------------------

- Rename icon. [sk2]

- Ultra -> CSR1000v. [sk2]

- Change mgmt interface handling. [sk2]

- More measure. [sk2]

- Update measure. [sk2]

- Tidying measurement. [sk2]

- Update user. [sk2]

- Regen autodoc. [sk2]

- Remove old measure code. [sk2]

- Working traceroute measurement. [sk2]

- Rebuild docs. [sk2]

- Change docs theme. [sk2]

- Doc -> docs. [sk2]

- Tidy. [sk2]

- Update ignore. [sk2]

- Tidying. [sk2]

v0.5.3 (2013-07-31)
-------------------

- Tidying setup.py. [sk2]

- Add new platform. [sk2]

- Tidying tests. [sk2]

- Restore. [sk2]

- Add comment. [sk2]

- Zmq measurement working (needs deserialization) [sk2]

- Zmq measure. [sk2]

- Testing, deployment. [sk2]

- Pep8, fix ibgp 2 layer issues. [sk2]

- Pep8. [sk2]

- Pep8. [sk2]

- Pep8. [sk2]

- Diff testing. [sk2]

- Remove unused code. [sk2]

- Add bgp pol tests. [sk2]

- More testing. [sk2]

- Change lo_interface to a valid linux/netkit name. [Olivier Tilmans]

- Split single compiler into modular platform and device compilers.
  [sk2]

- Tidying. [sk2]

- Loosen path tension. [sk2]

- Add testing to setup.py. [sk2]

- More cleanup. [sk2]

- Update tests. [sk2]

v0.5.2 (2013-07-24)
-------------------

- Sorting on ipv6 for stability. [sk2]

v0.5.1 (2013-07-24)
-------------------

- Sort for stability. [sk2]

- Natural sorting for bgp sessions. [sk2]

- Debug. [sk2]

- Sort for repeatability. [sk2]

- Merge onepk. [sk2]

- Allocate interfaces if not allocated on input. closes gh-180. [sk2]

- Apply correct subnet to interfaces. [sk2]

- Report node label rather than node id for string representation of
  interface. [sk2]

- Tidy. [sk2]

- Improvements. [sk2]

- Remove debug. [sk2]

- Fix issue with secondary loopbacks. [sk2]

- Tidy. [sk2]

- Store label on json. [sk2]

- More 3d. [sk2]

- More 3d. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- 3d prototype. [sk2]

- More 3d dev. [sk2]

- More 3d dev. [sk2]

- Three js dev. [sk2]

- Tidied. [sk2]

- Ignore dev project. [sk2]

- New icon. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Dont load ip allocs, labels by default. [sk2]

- Tidy logic. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Tidy, rename, add servers. [sk2]

- Tidy. [sk2]

- Add todo. [sk2]

- Dev. [sk2]

v0.5.0 (2013-07-02)
-------------------

- Tidy. [sk2]

- Split out ui. [sk2]

- Isis handling. [sk2]

- Setting with setattr for interface dict. [sk2]

- Isis combinations. [sk2]

- Better handling of ips. [sk2]

- Notes. [sk2]

- Split out webui. [sk2]

- More work to work with interfaces directly. [sk2]

- Tidying, check if bound interfaces. [sk2]

- Work on ip addressing if already set. [sk2]

- Ignore unbound interfaces. [sk2]

- Tidying. [sk2]

- Fixing ordering. [sk2]

- Tidying interface if set externally. [sk2]

- Clean up interface handling. [sk2]

- Less cryptic names, tidying. [sk2]

- Remap icons. [sk2]

- Add todos, better remote interface desc. [sk2]

- Copying attributes. [sk2]

- Better labelling, testing of interfaces. [sk2]

- Flip. [sk2]

- Handling of interfaces if allocated in physical. [sk2]

- Improve tension on paths. [sk2]

- Dev. [sk2]

- Able to search for edge by edge, used for cross-layer edge searches.
  [sk2]

- String function ensures string. [sk2]

- Interface errorr handling. [sk2]

- Handle numeric node ids. [sk2]

- More work on paths. [sk2]

- Dev. [sk2]

- Compress anm to send over wire. [sk2]

- Cdp on mgmt eth. [sk2]

- Add measure support. [sk2]

- Add path annotations. [sk2]

- Tidy. [sk2]

- Fixing interface access. [sk2]

- Fixing serialising. [sk2]

- Fix corner-case with building trees. [sk2]

- Add logging message. [sk2]

- Merge pull request #179 from sk2/custom-folders. [Simon Knight]

  Custom folders

- Work on new measure framework. [sk2]

- Initial work. [sk2]

- Toggle. [sk2]

- Remap the interfaces back to nodes, and integers. [sk2]

- Hash on edges. [sk2]

v0.4.9 (2013-06-14)
-------------------

- Fix bug with nx-os. [sk2]

- Better hashing for cross-layer and cross-anm/nidb interface
  comparison. [sk2]

- Add quiet (non verbose) option. [sk2]

- Test for presence in vrf graph. [sk2]

- Only add vrfs if at least one node has been tagged with vrf tag. [sk2]

- Turn web json stream back to anm/nidb. [sk2]

v0.4.8 (2013-06-12)
-------------------

- Ospfv3 on loopback zero. [sk2]

v0.4.7 (2013-06-12)
-------------------

- Tidy. [sk2]

- Add servers to igp. [sk2]

v0.4.6 (2013-06-11)
-------------------

- Disable bundled vis. [sk2]

- Update demo notebook. [sk2]

- Support for specific packages. [sk2]

- Update template. [sk2]

- Ignore ds store. [sk2]

- Add key filename support. [sk2]

- Split out args so can call programatically. [sk2]

  arg_string = "-f %s --deploy" % input_file args =
  console_script.parse_options(arg_string) console_script.main(args)

- Mark ipv4/ipv6 per interface, numeric ids. [sk2]

- Add l3 conn graph, use for vrfs. [sk2]

- Add dump. [sk2]

- Update entry point. [sk2]

- Update ignore. [sk2]

- Add tests. [sk2]

- Tidying compiler for interfaces. [sk2]

- Tidying, add option to force ank vis, add info message if single user
  mode activated. [sk2]

- Update to command line argument parsing. [sk2]

- Remove testing uuid. [sk2]

- Remove unused imports. [sk2]

- More multi-user support. [sk2]

- Tidy. [sk2]

- Use shorter uuid - less unique, but more usable. still unlikely to
  collide for our purposes. [sk2]

- Send uuid with highlight. [sk2]

- Tidy, add support for muti user. [sk2]

- Multi-user vis support. [sk2]

- Add todo. [sk2]

- Dont monitor build_network (won't work if using as module) [sk2]

- Add uuid support. [sk2]

- Support uuid. [sk2]

- Remove messaging call. [sk2]

- Remove highlight call. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

v0.4.5 (2013-05-29)
-------------------

- Use green for verified paths. [sk2]

- Use green for verified paths. [sk2]

- Use autonetkit_cisco web content if present. [sk2]

- Exception handling. [sk2]

- Add logging message. [sk2]

- Add logging message. [sk2]

- Fix logging. [sk2]

- Update demos. [sk2]

- Markdown extension of md not mmd. [sk2]

- Readme from .txt -> mmd. [sk2]

- Retry as markdown. [sk2]

- Add badge count using. [sk2]

- Demo updates. [sk2]

- More work on demo. [sk2]

- Further improved numeric vm id shutdown. [sk2]

- New demo notebook. [sk2]

- Clean paths on redraw. [sk2]

- Handle numeric vm ids. [sk2]

v0.4.4 (2013-05-15)
-------------------

- Dhcp management. [sk2]

- Add output target. [sk2]

- Fix global settings. [sk2]

- Add todo. [sk2]

- Updates to notebook. [sk2]

- Restore ui elements. [sk2]

- Link highlights behind nodes. [sk2]

- Add onepk stanza. [sk2]

- Updates. [sk2]

- Updates. [sk2]

- Demo notebook. [sk2]

- Highlight path colour. [sk2]

- Logging, highlight path colour. [sk2]

- Bugfix for highlights. [sk2]

- Bugfix. [sk2]

- Measure. [sk2]

- Add function to map edge attr to interfaces. [sk2]

v0.4.2 (2013-05-13)
-------------------

- Add code to switch on input extension. [sk2]

v0.4.1 (2013-05-10)
-------------------

- Don't put clns mtu on loopbacks. [sk2]

v0.3.14 (2013-05-10)
--------------------

- Enable clns mtu 1400 on isis interfaces. [sk2]

- Enable cdp per interface. [sk2]

- Enable cdp on all interfaces, rename mgmt interface. [sk2]

- Add ank_cisco to version. [sk2]

v0.3.13 (2013-05-10)
--------------------

- Mpls lite support for ios. [sk2]

- Only add PE, P to mpls_ldp. [sk2]

v0.3.12 (2013-05-10)
--------------------

- Use specified subnet. [sk2]

- Tidy. [sk2]

- Return interface on creation. [sk2]

- Updating ip allocations. [sk2]

- Refactored ip allocation. [sk2]

- Add comment. [sk2]

v0.3.11 (2013-05-09)
--------------------

- Mgmt + cdp. [sk2]

- Management toggle. [sk2]

- Tidying. [sk2]

- Rename function. [sk2]

- Support to copy across management info. [sk2]

- Allow [] notation to set/get overlay data. [sk2]

- Fix capitalisation. [sk2]

- Tidy. [sk2]

- Fix imports. [sk2]

- Fix import errors. [sk2]

- Don't over-write infrastructure blocks, closes gh-176. [sk2]

- Add comment. [sk2]

- Ensure allocation is imported. [sk2]

v0.3.10 (2013-05-04)
--------------------

- Catch value errors. [sk2]

- Fallback. [sk2]

v0.3.9 (2013-05-03)
-------------------

- Tidy management ips. [sk2]

- Explicitly set mgmt interface label for xr and nx-os. [sk2]

- Tidy. [sk2]

- Different ids based on ios derivative. [sk2]

- Tidy. [sk2]

- Nx-os interface labels. [sk2]

- Copy management subnet info if relevant. [sk2]

- Tidying. [sk2]

- Remove debug. [sk2]

- Use "use" with icon defs, rather than redefining each time. [sk2]

  based on
  https://groups.google.com/forum/?fromgroups=#!topic/d3-js/EtEwgOYnY6U
  better performance avoids the chrome caching issues

- Merge pull request #124 from oliviertilmans/http_vis. [Simon Knight]

  Fix a small log.info error

- Fix the following error: [Olivier Tilmans]

  > File "autonetkit/ank_messaging.py", line 107, in publish_data >
  log.info("Unable to connect to HTTP Server %s: e" % (http_url, e)) >
  TypeError: not all arguments converted during string formatting  When
  trying to generate cfg's without having the visualisation server
  running

- Treat specified interface labels per node rather than globally. [sk2]

- Make labels on top of links and nodes. [sk2]

- Add note. [sk2]

- Dont spuriously warn on unset. [sk2]

- Remove debug. [sk2]

- Fix error with interface names if not allocated, eg on a lan segment.
  [sk2]

- Remove unused code. [sk2]

- Ignore html coverage output. [sk2]

- Ignore coverage. [sk2]

- Rename validate to ank_validate to avoid conflict with configobj and
  paths. [sk2]

- Add IGP overlays even if not used - allows quicker test in compiler.
  [sk2]

- Include cluster attribute for rendering. [sk2]

- Show grouping for ibgp_v4 and ibgp_v6. [sk2]

- Resolve merge conflicts. [sk2]

- Tidy ignore. [sk2]

- Fix single-node hulls: make slightly bigger so don't get printing
  artifacts with gap in middle. [sk2]

- Merge pull request #116 from oliviertilmans/cleanup. [Simon Knight]

  Minor cleanup & usage of os.path.join

- Merge pull request #119 from oliviertilmans/device_type_server. [Simon
  Knight]

  (Fix Issue #117) Using Any other non router l3device node (i.e.
  server) crashes ANK

- Merge pull request #118 from sdefauw/master. [Simon Knight]

  Bug of boolean fields in graphml solved.

- Hostname is now independent from zebra. [Olivier Tilmans]

- Merge branch 'device_type_server' into anycast_dns_resolver. [Olivier
  Tilmans]

- Start zebra only if the node needs it (is a router at the moment)
  [Olivier Tilmans]

- Added anycast ip attribute. [Olivier Tilmans]

- Add anycast dns resolver support on ANK side, anycast ip's have yet to
  handled. [Olivier Tilmans]

- * Allow the server nodes (and by extension all l3devices) to be real
  netkit VM's * Make the start of the zebra daemon optional (only if one
  of its component is in use) * Made sure that the debug flag for BGP
  was only set if BGP was enabled in the node. [Olivier Tilmans]

- Ensure that copy_edge_attr_from will only copy attributes from edges
  which are common to the two graphs. [Olivier Tilmans]

- Bug of boolean fields in graphml solved. [Sébastien De Fauw]

- Enforced usage of os.path.join in compiler. [Olivier Tilmans]

- Remove redundant overlay creations. [Olivier Tilmans]

- Clean out last of pika references. [sk2]

- Tidying messaging. [sk2]

- Use new format messaging. [sk2]

- Using url params for routing, stripping out rabbitmq and telnet. [sk2]

- Tidying up json format. [sk2]

- Uncompress notebooks for easier access. [sk2]

- Compress ipython notebooks. [sk2]

- Remove symlink. [sk2]

- Use gzip for default (smaller file size) [sk2]

- Use gzip for default json. [sk2]

- Remove unused data. [sk2]

- Only apply ospf to interfaces bound in ospf graph. [sk2]

- Remove images from tutorial. [sk2]

v0.3.7 (2013-04-15)
-------------------

- Update packages to latest version. [sk2]

- Remove message pipe using telnet, support tornado 3.0.1. [sk2]

v0.3.6 (2013-04-15)
-------------------

- Add images. [sk2]

- New module to push changes. [sk2]

- Split out functions. [sk2]

- Allow search on node id as well as label. [sk2]

- Convert multi -> single edge graph. [sk2]

- Split out functions. [sk2]

- Split out functions. [sk2]

- Allow select edge by nodes. [sk2]

- Example notebook on OSPF cost experiments. [sk2]

- Inc version. [sk2]

- Split the boolean to render to_memory, and the rendered output. [sk2]

- Tidying. [sk2]

- Split out initialise into new function. [sk2]

- New diff script to monitor and update network. [sk2]

- Update. [sk2]

- Modify example input. [sk2]

- Add support for trace colours. [sk2]

- Updates to traces. [sk2]

- Index edges by src/dst pair. [sk2]

- Add note. [sk2]

- Comment out highlight. [sk2]

- Allow access interface by numeric value (eg if from diff output) [sk2]

- Add support for show ip ospf and conf t. [sk2]

- Add function to diff two nidbs. [sk2]

- Add basic processing (this needs to be moved to a process module)
  [sk2]

- Increase management subnet pool for testing (this needs to be modified
  later) [sk2]

- Don't set ibgp for grid. [sk2]

- Remove extra update. [sk2]

- Allow path data. [sk2]

- More work on path animations. [sk2]

- Animated path plotting. [sk2]

- Change marker colour. [sk2]

- Mapping from node id to id, ensures unique. [sk2]

- Tidying. [sk2]

- Improve path plotting, add markers (arrows) [sk2]

- Groupings for nodes, edges, etc: can control ordering. [sk2]

- Notify when receive highlight. [sk2]

- Storing measured data to json. [sk2]

- Improvements to automated measurement: use iteration rather than
  callbacks. [sk2]

- Tidying, show verification results. [sk2]

- Set ospf for quagga. [sk2]

- Sort cd ids. [sk2]

- Basic shell script to run measure periodically. [sk2]

  will later be replaced with pure python script run as part of
  autonetkit (or autonetkit_measure) command

- Data and script to replay measurements. [sk2]

- New verify module. [sk2]

- Sort names for split. [sk2]

- Better trace highlight support. [sk2]

- Add sh ip route support. [sk2]

- Bugfix: only validate if anm loaded. [sk2]

- Remove old code. [sk2]

- Add support for parsing sh ip route from quagga. [sk2]

- Support for highlight paths [node, node, ... node] [sk2]

- Support for highlight paths. [sk2]

- Asn 0 -> 1. [sk2]

- Remove trailing comma which made loopback ip a tuple. [sk2]

- Support topology data used to store data without a template to render.
  [sk2]

- More work on oob ips. [sk2]

- Better handling for non existent interfaces - eg oob added to nidb.
  [sk2]

- Allow interfaces to be added to nidb. [sk2]

- Adding oob support. [sk2]

- More work on vrfs. [sk2]

- Tidy .gitignore. [sk2]

- Ignore *.graphml* files. [sk2]

- New collision domain icon. [sk2]

- Remove symlink that crept in. [sk2]

- Remove point-to-point config statement for ospf. [sk2]

- Use same variable name for vpnv4. [sk2]

- Tidying vrf pre-process for ibgp. [sk2]

- Enforce specific packages. [sk2]

- Change default edge color. [sk2]

- Send ipv4 infra as json. [sk2]

- Convert areas to strings for serializing keys. [sk2]

- Add docstrings. [sk2]

- Sort returned json keys. [sk2]

- Continued vrfs. [sk2]

- Ibgp vrf. [sk2]

- Work on vrfs and bgp sessions, tidied up bgp sessions. [sk2]

- More work on bgp vrfs. [sk2]

- More work on vrfs. [sk2]

- Remove debugging. [sk2]

- Add to mpls ldp if bound in that overlay. [sk2]

- Copy description as well as type from anm. [sk2]

- Add todo. [sk2]

- Smaller interface labels. [sk2]

- Allow access to interface from nidb. [sk2]

- Remove testing code. [sk2]

- Work on vrfs, mpls ldp. [sk2]

- Work on mpls, vrfs, mpls ldp. [sk2]

- Fix issue with interface descriptions for secondary loopbacks. [sk2]

- Copy interface ids back from nidb to anm overlays, condense to brief
  for brevity. [sk2]

- Update doc, work on json tree for nidb. [sk2]

- Merge pull request #115 from sk2/master. [Simon Knight]

  merge back to interfaces

- Merge pull request #114 from sk2/validate. [Simon Knight]

  add validation tests for ipv4

- Merge pull request #113 from sk2/interfaces. [Simon Knight]

  Interfaces

- Add validation tests for ipv4. [sk2]

- Initial commit of validate. [sk2]

- Remove specific code, works under generic interface attributes. [sk2]

- Add hooks for validate enable/disable. [sk2]

- Workaround to import validate from python system, namespace clash with
  using validate inside ank. [sk2]

- Shortcut to check if interface is physical. [sk2]

- Interface font size. [sk2]

- Simpler cd icon. [sk2]

- More work on vrfs. [sk2]

- Generic interface overlay groupings (to support vrfs and ospf in
  consistent format, will auto adapt) [sk2]

- V6 secondary loopback alloc. [sk2]

- Add shortcuts to interface iteration by type. [sk2]

- Fix comment. [sk2]

- Define lt for interface comparisons. [sk2]

- Optional handling of secondary loopbacks. [sk2]

- Tidy. [sk2]

- Copying v4 and v6 ips for secondary loopbacks. [sk2]

- Tidying vrf interfaces. [sk2]

- Merge pull request #112 from sk2/interfaces. [Simon Knight]

  Interfaces

- Ipv4/v6 switches. [sk2]

- More work on tidying v4, v6, interfaces, testing. [sk2]

- More interface hulls. [sk2]

- Tidy icons. [sk2]

- Debug. [sk2]

- Inc ver. [sk2]

- Update. [sk2]

- New icon. [sk2]

- Interface hulls. [sk2]

- Bugfixes. [sk2]

- Add accessors for physical and loopback access. [sk2]

- More work on interfaces. [sk2]

- Fix ibgp layering. [sk2]

- More interface work. [sk2]

- More interfaces. [sk2]

- More interface work. [sk2]

- More work on interfaces. [sk2]

- More work on interfaces: datastructures, api, build, compile. [sk2]

- Fixes for interfaces. [sk2]

- Partial code for interface groupings eg for ospf areas. [sk2]

- Working interface mappings in nidb. [sk2]

- Remove debug. [sk2]

- Copying across interface type to nidb. [sk2]

- Interface dev. [sk2]

- Adding notes. [sk2]

- Fix order: first param if using args eg ("description") is desc not
  type. [sk2]

- Fix bug: need to test overlay_id is phy, not node_id is phy. [sk2]

- Fix docstring. [sk2]

- Add note. [sk2]

- Return type. [sk2]

- Tidy. [sk2]

- Remove unneeded check (as fixed bug in ank split) [sk2]

- Fix bug: was copying interface id from src rather than dst. [sk2]

- Add todo. [sk2]

- Add todo. [sk2]

- Expand out _interfaces for edges. [sk2]

- More dev work on interfaces. [sk2]

- Looking up interfaces in nidb. [sk2]

- Better adding edges to nidb if from cd vs switch. [sk2]

- Better adding edges to nidb if from cd vs switch. [sk2]

- Edge comparisons. [sk2]

- Debug. [sk2]

- Workarounds for multipoint ospf. [sk2]

- Workarounds for multipoint ospf. [sk2]

- Merge pull request #111 from sk2/multipoint. [Simon Knight]

  Multipoint

- Make single-node groups less bubble-y. [sk2]

- Tidy. [sk2]

- Update ebgp to handle switches. [sk2]

- Fix bugs in explode. [sk2]

- Fix multipoint ebgp session handling to obtain ips. [sk2]

- Switch support for isis, ospf, ebgp. [sk2]

- Handle connected components. [sk2]

- Concat rather than nested lists. [sk2]

- Add todo. [sk2]

- Fix support for wrapping exploded edges. [sk2]

- Look at neighbouring routers. [sk2]

- Only look at neighbouring routers for vrf (handles switches, other
  devices) [sk2]

- Fix bug where passing in empty list would fall back to all nodes in
  graph. [sk2]

  now check if nbunch is None rather than evaluating to False (which was
  case for empty list)

- Merge pull request #110 from sk2/master. [Simon Knight]

  merge updates back to vrf branch

- Fix issue with ibgp levels. [sk2]

- More work on interfaces. [sk2]

- Updating interface support. [sk2]

- Testing code for interfaces. [sk2]

- Testing code for interfaces. [sk2]

- Correct returning edges to use new interface binding format of
  {node_id: interface_id} [sk2]

- Access corresponding interface across overlays (if exists) [sk2]

- String repr of anm. [sk2]

- New function for testing if overlay present in anm. [sk2]

- Retain relevant interface bindings when splitting edges. [sk2]

- Merge pull request #108 from sk2/multi-edge. [Simon Knight]

  Multi edge

- Inc ver. [sk2]

- Fix problem with one or two collision domain ASes. [sk2]

- Handle case of AS with no iBGP nodes (all set to ibgp_role of None)
  [sk2]

- Updates. [sk2]

- Fix correct image. [sk2]

- Fix right version. [sk2]

- Update. [sk2]

- Updates. [sk2]

- Updates. [sk2]

- More updates. [sk2]

- Updates. [sk2]

- Updates. [sk2]

- Updates. [sk2]

- Revert change. [sk2]

- Move to work with online notebook viewer. [sk2]

- Update images, add images to tutorial. [sk2]

- Update tutorial. [sk2]

- Increase timeout. [sk2]

- Add tutorial graphml. [sk2]

- Add tutorial images. [sk2]

- Remove debug. [sk2]

- Update tutorial. [sk2]

- Inc ver. [sk2]

- Updates. [sk2]

- Use ipv4 not ip. [sk2]

- Tidy. [sk2]

- New path colours. [sk2]

- Handling starting and lab started. [sk2]

- Better debug. [sk2]

- Use ipv4 overlay. [sk2]

- Add todo. [sk2]

- Tidying, add option for grid. [sk2]

- Default ospf cost. [sk2]

- Ensure ospf cost is int. [sk2]

- Add 2d grid. [sk2]

- Bugfix. [sk2]

- More work on vrfs. [sk2]

- Remove website (has been moved to gh-pages branch) [sk2]

- Inc ver. [sk2]

- Closes gh-91. [sk2]

- Extra send option. [sk2]

- More explicit boolean. [sk2]

- Remove debug. [sk2]

- Workaround for gh-90. [sk2]

- Auto list contributors from github api. [sk2]

- Set default igp. [sk2]

- Bugfix: dont set if node not in graph. [sk2]

- Extend tutorial examples. [sk2]

- Allow type casting in copy edge and node attribute functions. [sk2]

- Update tutorial. [sk2]

- Add tutorial. [sk2]

- Move to gist. [sk2]

- More notebook updates. [sk2]

- Update workbook. [sk2]

- Example ipython notebook. [sk2]

- Highlights for nodes and edges. [sk2]

- Inc ver. [sk2]

- White body for printing. [sk2]

- Merge ospf areas back into general function. [sk2]

- Search for edges based on src/dst string ids. [sk2]

- Simplified access to update http. [sk2]

- Add shortcuts to common classes/functions. [sk2]

- Merge pull request #88 from metaswirl/master. [Simon Knight]

  First pull request :)

- Merge pull request #89 from bhesmans/fixCache. [Simon Knight]

  fixe cache issue.

- Fixe cache issue. [Hesmans Benjamin]

  Won't render otherwise  the two path joined were both absolute. Now,
  use relative "base" isntead of full_base to build the base_cache_dir

- Cleaned comments. [Niklas Semmler]

- Added isis support to quagga, fixed a bug in the renderer. [Niklas
  Semmler]

- Tidying code. [sk2]

- Add offset to fix truncating of curved edges to boxes in 2 node group
  plots. [sk2]

- Fix ordering of functions. [sk2]

- Tidy. [sk2]

- Pep8, tidying. [sk2]

- Tidying. [sk2]

- Tidying vrfs. [sk2]

- Merge pull request #86 from sk2/vrf. [Simon Knight]

  Vrf support, misc bugfixes + improvements

- Fix merge. [sk2]

- Auto set ce. [sk2]

- Remove todo. [sk2]

- Merge pull request #85 from bhesmans/fixRRClientAS. [Simon Knight]

  quick fix for RR: no remote as.

- Remove offset. [sk2]

- Vrfs. [sk2]

- Bugfix. [sk2]

- Handle socket in use. [sk2]

- Quick fix for RR: no remote as. [Hesmans Benjamin]

- Work on caching. [sk2]

- Use set comprehensions. [sk2]

- Tidy. [sk2]

- Move utility function. [sk2]

- Code tidy. [sk2]

- Pep8. [sk2]

- Merge pull request #65 from oliviertilmans/master. [Simon Knight]

  Clear out .svn subdir from doc/source/reference/

- Updated gitignore to avoid further accidental tracking of .svn
  subdirs. [Olivier Tilmans]

- Removed svn subdir. [Olivier Tilmans]

- Ios v6 isis. [sk2]

- Add template error rendering. [sk2]

- Ospfv3 on ios. [sk2]

- Tidy status output. [sk2]

- Marking for ospf v3. [sk2]

- Attempts to tidy zoom. [sk2]

- Increment version. [sk2]

- Fix indent, add process id for isis. [sk2]

- Bugfix:  126 ->128 bit v6 loopbacks. [sk2]

- More work on interfaces, secondary loopbacks, vrfs. [sk2]

- More interface support. [sk2]

- Allocate to secondary loopbacks. [sk2]

- Initial vrf block. [sk2]

- More vrf. [sk2]

- Improved interface handling. [sk2]

- Update github link ank_v3_dev -> autonetkit. [sk2]

- More work on interfaces: store on physical graph if node exists in it.
  allows consistent interfaces across layers. [sk2]

- Toggle filter. [sk2]

- Neater filter. [sk2]

- Inc ver. [sk2]

- Toggle filter. [sk2]

- Add extra log message. [sk2]

- Load opacity on enter. [sk2]

- Filter long attribute lists. [sk2]

- Remove debug. [sk2]

- Node filtering. [sk2]

- Work on filtering opacity. [sk2]

- Increment version. [sk2]

- Check l3 cluster for ibgp, tidy syntax. [sk2]

- Fix quagga. [sk2]

- Work on interfaces. [sk2]

- Attribute filtering for neighbors. [sk2]

- Take icon size into account for auto scaling. [sk2]

- Add grouping for vrf. [sk2]

- Interfaces: adding with attributes, filtering on attributes,
  iteration. [sk2]

- Error handling. [sk2]

- Adding vrf config. [sk2]

- Tidy v6 access, format for consistency. [sk2]

- Renaming ip -> ipv4, ip6 -> ipv6. [sk2]

- Only configure v4 or v6 address blocks if v4 or v6 respectively is
  enabled. [sk2]

- Add note. [sk2]

- Fix ipv4 var. [sk2]

- Tidy debug. [sk2]

- More work on nx_os. [sk2]

- Initial work for nxos. [sk2]

- Updates to allow dual-stack for cisco. [sk2]

- Update scale for resized initial. [sk2]

- Inc version. [sk2]

- Tidy syntax. [sk2]

- Tidying example access syntax. [sk2]

- Better default scale for large topologies. [sk2]

- Rename icon to descriptive label. [sk2]

- Fix var names. [sk2]

- Fix order of description. [sk2]

- Set config dir, fix chassis. [sk2]

- Add todo note. [sk2]

- Fix error handling. [sk2]

- Default to memory. [sk2]

- Fix quagga ip format. [sk2]

- Set dynagen config directory. [sk2]

- Tidy dynagen. [sk2]

- Toggle off v6. [sk2]

- Use 7200 image. [sk2]

- Add functions to nidb to be closer to anm. [sk2]

- Ospf cost support. [sk2]

- Enable v6. [sk2]

- Fix level support for ibgp from yed. [sk2]

- Update add_edge attr. [sk2]

- Update. [sk2]

- Initial commit of dynagen code for gh-46. [sk2]

- Handle no ip6 graph. [sk2]

- Remove overlay_accessor: use either anm['overlay_id'] or
  G_a.overlay("overlay_id") [sk2]

- Access overlay directly. [sk2]

- Support v6. [sk2]

- Support v6. [sk2]

- Add groupby independent of subgraph. [sk2]

- Add library for # [sk2]

- Info -> debug. [sk2]

- Increment version. [sk2]

- Add # library. [sk2]

- Tidy logic, add l3 to ibgp clustering. [sk2]

- Look for correct package name. [sk2]

- Tidy. [sk2]

- Tidying, adding from HRR->RR if same RR group. [sk2]

- Add extra logging information. [sk2]

- Remove debug. [sk2]

- Change interface allocations. [sk2]

- Simplifying. [sk2]

- Tidy to use routers. [sk2]

- Exclude _interfaces from edge tooltip. [sk2]

- Fix websocket tooltip. [sk2]

- Add deploy wrapped, tidy. [sk2]

- Tidy syntax. [sk2]

- Tidy. [sk2]

- Add routers shortcut. [sk2]

- Support ibgp l1->l3 if not l2 in ibgp_l3_cluster. [sk2]

- Add ignores. [sk2]

- Update ignore. [sk2]

- Add fonts to manifest. [Simon Knight]

- Remove other deps. [Simon Knight]

- Update setup. [Simon Knight]

- Update version. [Simon Knight]

- Update icons folder. [Simon Knight]

- Merge pull request #64 from sk2/development. [Simon Knight]

  Development

- Handle pika. [sk2]

- Merge pull request #63 from sk2/master. [Simon Knight]

  push

- Merge pull request #62 from sk2/Stable. [Simon Knight]

  improvements to measurement and traceroute plotting

- Improvements to measurement and traceroute plotting. [sk2]

- Merge pull request #61 from sk2/development. [Simon Knight]

  Development

- Disable measure by default. [sk2]

- Remove debug. [sk2]

- Add bootup circles. [sk2]

- Show websocket state as icon. [sk2]

- Merge pull request #60 from sk2/development. [Simon Knight]

  Development

- Add example. [sk2]

- Merge pull request #59 from sk2/development. [Simon Knight]

  Development

- Remove debug. [sk2]

- More features. [sk2]

- Exit for paths. [sk2]

- Bugfix. [sk2]

- Allow direct messaging using messaging rather than manual rabbitmq
  construction. [sk2]

- Merge pull request #58 from sk2/development. [Simon Knight]

  Development

- Tidy. [sk2]

- Example updates. [sk2]

- Bugfix. [sk2]

- Measure client updates. [sk2]

- Change import order. [sk2]

- More updates. [sk2]

- Take rmq as argument. [sk2]

- Add measure client. [sk2]

- Merge pull request #57 from sk2/development. [Simon Knight]

  tidy

- Ignore rendered. [sk2]

- Tidy. [sk2]

- Merge pull request #56 from sk2/development. [Simon Knight]

  move example to base dir

- Move example to base dir. [sk2]

- Merge pull request #55 from sk2/development. [Simon Knight]

  Development

- Work on example. [sk2]

- Update default log. [sk2]

- More icon. [sk2]

- Example. [sk2]

- More icon. [sk2]

- More icon. [sk2]

- Merge pull request #54 from sk2/development. [Simon Knight]

  Development

- Remove egg info. [sk2]

- Tidy. [sk2]

- Update icon. [sk2]

- Move vis folder. [sk2]

- Update packaging dependencies. [sk2]

- Update doc, setup config. [sk2]

- Merge pull request #53 from sk2/interfaces. [Simon Knight]

  Interfaces

- Add dependencies. [sk2]

- Add icons to ui. [sk2]

- Merge pull request #52 from sk2/interfaces. [Simon Knight]

  Interfaces

- Update icon. [sk2]

- Remove old messaging package. [sk2]

- Merge pull request #51 from sk2/interfaces. [Simon Knight]

  Interfaces

- Move to examples directory. [sk2]

- Add zoom fit button. [sk2]

- Update vis layout. [sk2]

- Update year, add favico to website. [sk2]

- Icon data. [sk2]

- Update icon. [sk2]

- Auto zoom, remove interfaces and labels. [sk2]

- Dont hide labels. [sk2]

- Add icon. [sk2]

- Remove unused messaging. [sk2]

- Ui tidy. [sk2]

- Revert. [sk2]

- Auto hide revisions, tidy general ui, remove interfaces with toggle.
  [sk2]

- Tidying. [sk2]

- Merge pull request #50 from sk2/interfaces. [Simon Knight]

  Merge

- Add docs to repo. [sk2]

- Remove unused python package. [sk2]

- Add note. [sk2]

- Add icon. [sk2]

- Add todo. [sk2]

- Better node handling. [sk2]

- Remove debug. [sk2]

- Tidying. [sk2]

- Simpler add edges wrapper. [sk2]

- Tidy manifest. [sk2]

- Set default for blank labels, better handling of non-unique labels: if
  so then set with asn. [sk2]

- Handle multi-as from zoo. [sk2]

- Tidying. [sk2]

- Add ip. [sk2]

- Processing for nren 1400. [sk2]

- Simple example. [sk2]

- More example. [sk2]

- More examples. [sk2]

- Set False for yEd exported booleans (by default not present on a node)
  [sk2]

- Tidy simple. [sk2]

- Add retain to adding nodes through add_overlay. [sk2]

- Add build option. [sk2]

- Tidy simple example. [sk2]

- Add examples. [sk2]

- Tidy logic. [sk2]

- New simplified example. [sk2]

- Tidy, toggle out publishing v6 topology. [sk2]

- Use new add overlay format. [sk2]

- Add ability to add nodes at overlay creation. [sk2]

- Merge pull request #43 from sk2/interfaces. [Simon Knight]

  Interfaces

- V6 overlay support and allocation done. [sk2]

- Optional server param for messaging: not required if using http post,
  as picked up from settings. [sk2]

- Adding ipv6 support. [sk2]

- Increment version. [sk2]

- Support import of cisco templates. [sk2]

- Move more cisco specific code out. [sk2]

- Move cisco specific load and deploy to autonetkit_cisco module. [sk2]

- Update doc. [sk2]

- Increment. [sk2]

- Ensure area is string. [sk2]

- Initial work on highlighting shared interfaces (eg loopback0) [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Remove unused allocate_hardware. [sk2]

- Add interface labels. [sk2]

- Tidying debug. [sk2]

- More interfaces. [sk2]

- More improvements to interfaces. [sk2]

- More work on interfaces - work in progress. [sk2]

- More work on vis. [sk2]

- Display interfaces for directed edges. [sk2]

- Bigger font for edges. [sk2]

- Much improved directed edges, now with labels on the edge. [sk2]

- Redoing directed edges. [sk2]

- Dev. [sk2]

- Dev. [sk2]

- Disable zoom. [sk2]

- Initial work on dynamic zooming. [sk2]

- Remote message pipe from setup guide. [sk2]

- Merge pull request #40 from sk2/interfaces. [Simon Knight]

  tidy

- Tidy. [sk2]

- Merge pull request #39 from sk2/interfaces. [Simon Knight]

  Interfaces

- Disable full hostnames. [sk2]

- Increment version. [sk2]

- Lower node labels. [sk2]

- Lower node labels. [sk2]

- Tidy. [sk2]

- Tidy. [sk2]

- Better option to disable edge labels. [sk2]

- Don't display interfaces. [sk2]

- Better handling of interfaces in tooltip. [sk2]

- Add option to disable edge labels. [sk2]

- Tidy area zero handling. [sk2]

- Handle ip address format for ospf areas. [sk2]

- Tidy, todos. [sk2]

- Correct rendering of arrays in tooltips. [sk2]

- Interface toggle. [sk2]

- More improvements for interfaces. [sk2]

- Better interface vis. [sk2]

- Add interfaces to anm, render interfaces on vis. [sk2]

- Store ospf areas on node. [sk2]

- Upgrade d3 from v2 to v3. [sk2]

- Use v3 of d3, hide history buttons. [sk2]

- Alignment, grouping for ospf areas. [sk2]

- Tidy. [sk2]

- Correct docstring. [sk2]

- Merge pull request #38 from sk2/dev. [Simon Knight]

  default netkit render

- Default netkit render. [sk2]

- Merge pull request #37 from sk2/dev. [Simon Knight]

  better web message

- Better web message. [sk2]

- Merge pull request #36 from sk2/dev. [Simon Knight]

  Dev

- Ignore. [sk2]

- Add tornado to base dependencies. [sk2]

- Error handling. [sk2]

- Error handling if no input file. [sk2]

- Better desc string. [sk2]

- Disable pika requirement for base install. [sk2]

- Enable http post by default. [sk2]

- Merge pull request #35 from sk2/dev. [Simon Knight]

  Merge latest updates

- Set input label for other device types, used in post-processing
  module. [Simon Knight]

- Support manually specified interface names. [Simon Knight]

- Tidy. [Simon Knight]

- Support manually specified interface names. [Simon Knight]

- New messaging module. [Simon Knight]

- Better error handling for invalid category ids. [Simon Knight]

- Fix syntax error in logging. [Simon Knight]

- Add end statement. [Simon Knight]

- Handle extra attribute. [Simon Knight]

- Copy across extra attribute. [Simon Knight]

- Support for specified interface names. [Simon Knight]

- Tidying. [Simon Knight]

- Update look and feel. [Simon Knight]

- Rename ank_pika to more generic messaging module. [Simon Knight]

- Increment version. [Simon Knight]

- Add new icons. [Simon Knight]

- Tidy http post, support manually specified IPs. [Simon Knight]

- Updates to logging. [Simon Knight]

- Merge pull request #34 from sk2/dev. [Simon Knight]

  iBGP hierarchies, HTTP Post to update web ui

- Tweak line offsets. [Simon Knight]

- Support HTTP POST for updating topologies. [Simon Knight]

- Fix indent. [Simon Knight]

- Group by l3 cluster. [Simon Knight]

- Tweaks to vis. [Simon Knight]

- Update taper. [Simon Knight]

- More tapered edges. [Simon Knight]

- Update ignore. [Simon Knight]

- Tidy neighbors. [Simon Knight]

- Ibgp hierarchies. [Simon Knight]

- Tapered edges. [Simon Knight]

- Merge pull request #33 from sk2/dev. [Simon Knight]

  route reflectors

- Corrections to iBGP. [Simon Knight]

- Seperate out address classes. [Simon Knight]

- Seperate out address classes. [Simon Knight]

- Remove debug. [Simon Knight]

- Route reflectors. [Simon Knight]

- Merge pull request #32 from sk2/dev. [Simon Knight]

  IOS IGP, bugfix for single-AS loopbacks

- Fix single-AS loopbacks. [Simon Knight]

- Hover for ip address nodes. [Simon Knight]

- Interface type. [Simon Knight]

- Tidy. [Simon Knight]

- Fix network format. [Simon Knight]

- Merge pull request #31 from sk2/dev. [Simon Knight]

  Dev

- Add isis support to ios. [Simon Knight]

- Tidy. [Simon Knight]

- Merge pull request #30 from sk2/dev. [Simon Knight]

  Dev

- Issue with configspec, update areas. [Simon Knight]

- Set syntax from config defaults. [Simon Knight]

- Merge pull request #29 from sk2/dev. [Simon Knight]

  fixes to ios config, interface naming, separate loopback IP groups:
  don't allocate 10.0.0.0 etc as a loopback

- Seperate loopback groups: don't allocate 10.0.0.0 as a loopback.
  [Simon Knight]

- Allocated loopbacks in a group: don't want 10.0.0.0 as a loopback ip.
  [Simon Knight]

- Add point-to-point to networks. [Simon Knight]

- Id format Ethernet x/0. [Simon Knight]

- Option to toggle timestamp in rendered output. [Simon Knight]

- Handle socket error with warning. [Simon Knight]

- Merge pull request #28 from sk2/dev. [Simon Knight]

  website updates, add readme

- Update website, add readme. [Simon Knight]

- Fix github link. [Simon Knight]

- Update css page references, title in using. [Simon Knight]

- New website. [Simon Knight]

- Merge pull request #27 from sk2/dev. [Simon Knight]

  Dev

- Tidy loading. [Simon Knight]

- Default ospf area for graphml. [Simon Knight]

- Update defaut topology for vis. [Simon Knight]

- Merge pull request #26 from sk2/dev. [Simon Knight]

  add edge labels, restore print css, hierarchical ospf for IOS

- More hierarchical ospf config. [Simon Knight]

- Ospf hierarchy. [Simon Knight]

- Fix print css. [Simon Knight]

- Edge labels. [Simon Knight]

- Merge pull request #24 from sk2/dev. [Simon Knight]

  remove debug, update github link to dev alpha

- Update github link to dev alpha. [Simon Knight]

- Remove debug. [Simon Knight]

- Merge pull request #23 from sk2/dev. [Simon Knight]

  Optional render, adding node label and edge group dropdowns, add ospf
  areas, tipsy for tooltips

- Default area of 0. [Simon Knight]

- Redrawing changed edge_group_id. [Simon Knight]

- Hide infobar, larger font for yapsy. [Simon Knight]

- Use tipsy for tooltips. [Simon Knight]

- Add OSPF router type. [Simon Knight]

- Add title on hover, tidying. [Simon Knight]

- Work on ospf areas. [Simon Knight]

- Support for node label and edge grouping. [Simon Knight]

- Add comments. [Simon Knight]

- Add dropdowns for node label and edge grouping. [Simon Knight]

- Add underscore js library. [Simon Knight]

- Add render option. [Simon Knight]

- Merge pull request #22 from sk2/dev. [Simon Knight]

  bugfix for ip if no links, add support for nested grouping in vis
  (used for ospf attributes)

- Fix ip crash if no links. [Simon Knight]

- Remove debug, copy ospf_area into "area" in ospf graph. [Simon Knight]

- Support ospf areas, nested groupings. [Simon Knight]

- More parameters for copy_attr_from. [Simon Knight]

- Merge pull request #16 from sk2/dev. [Simon Knight]

  Improvements to packaging for textfsm templates, add demo video to
  website, fix passive interface for quagga IGP

- Add demo video. [Simon Knight]

- Correct path. [Simon Knight]

- Open traceroute template from package. [Simon Knight]

- Use package template file. [Simon Knight]

- Update textfsm include. [Simon Knight]

- Include textfsm templates. [Simon Knight]

- Non numeric first character for zebra hostname too. [Simon Knight]

- Make sure quagga hostnames start with letter. [Simon Knight]

- Passive interfaces for ebgp. [Simon Knight]

- Add loopback to interfaces. [Simon Knight]

- Handle empty key string. [Simon Knight]

- Merge pull request #15 from sk2/dev. [Simon Knight]

  Dev

- Make screencasts more visible. [Simon Knight]

- Change ip ranges. [Simon Knight]

- Add alpha sorting for machines. [Simon Knight]

- Use interface id. [Simon Knight]

- Add sorting. [Simon Knight]

- Add text sorting. [Simon Knight]

- Start loopbacks at 172.16.127 so don't interfere with taps. [Simon
  Knight]

- Don't clobber measure. [Simon Knight]

- Less verbose messages. [Simon Knight]

- Better output. [Simon Knight]

- Add note. [Simon Knight]

- Merge pull request #13 from sk2/dev. [Simon Knight]

  drive compilation from config file

- Drive compilation from config file. [Simon Knight]

- Merge pull request #12 from sk2/dev. [Simon Knight]

  Dev

- Add publications. [Simon Knight]

- Remove debug. [Simon Knight]

- Neater maximise display. [Simon Knight]

- Handle case of no infrastructure ips to advertise. [Simon Knight]

- Allocate loopbacks seperately to infra, closes gh-10. [Simon Knight]

- Add css maximise option. [Simon Knight]

- Merge pull request #11 from sk2/dev. [Simon Knight]

  Cleaner updating to web interface

- Read updates. [Simon Knight]

- Remove extra sending pika. [Simon Knight]

- Remove debug. [Simon Knight]

- Merge pull request #9 from sk2/dev. [Simon Knight]

  Basic lat/lon to x/y from zoo, grid layout if no x/y set

- Add comment. [Simon Knight]

- Merge pull request #8 from sk2/dev. [Simon Knight]

  Dev

- Support for reading from stdin, writing single-file templates into
  memory. [Simon Knight]

- Use argparse instead of deprecated optparse. [Simon Knight]

- Support html in status: lists rather than block of text. [Simon
  Knight]

- Merge pull request #7 from sk2/dev. [Simon Knight]

  Dev

- Update instructions. [Simon Knight]

- Inc. [Simon Knight]

- Update isis format. [Simon Knight]

- Default isis metric. [Simon Knight]

- Merge pull request #6 from sk2/dev. [Simon Knight]

  Dev

- Merge pull request #5 from sk2/master. [Simon Knight]

  Dev

- Dont warn if no rmq. [Simon Knight]

- Merge pull request #4 from sk2/dev. [Simon Knight]

  Dev

- Update tutorial. [Simon Knight]

- Inc. [Simon Knight]

- Better handling of timestamp. [Simon Knight]

- Include quagga templates. [Simon Knight]

- Disable file logging for now. [Simon Knight]

- Default to compile. [Simon Knight]

- Don't write overlays as graphml. [Simon Knight]

- Merge pull request #3 from sk2/master. [Simon Knight]

  Merge website and templates

- Add tutorial. [Simon Knight]

- Inc ver. [Simon Knight]

- Include quagga templates. [Simon Knight]

- Merge pull request #2 from sk2/dev. [Simon Knight]

  Better defaults and compilation

- Better compilation depending on presence of platform/host. [Simon
  Knight]

- Update graphml default. [Simon Knight]

- Remove debug. [Simon Knight]

- Merge pull request #1 from sk2/dev. [Simon Knight]

  Dev

- Add development install guide. [Simon Knight]

- Increment version. [Simon Knight]

- Update interface names. [Simon Knight]

- Add youtube link for screencasts. [Simon Knight]

- Increment version, include html data in package. [Simon Knight]

- Support telnet sockets. [Simon Knight]

- Use new load module. [Simon Knight]

- More visible trace data. [Simon Knight]

- Remove debug. [Simon Knight]

- Sorting edges. [Simon Knight]

- Tidying. [Simon Knight]

- More visible traceroutes. [Simon Knight]

- Add support for telnet. [Simon Knight]

- Move vis inside distro. [Simon Knight]

- Updates. [Simon Knight]

- Use ank vis in distro. [Simon Knight]

- Increment version. [Simon Knight]

- Include vis in distro. [Simon Knight]

- Increment version. [Simon Knight]

- Fix naming. [Simon Knight]

- Comment out dev. [Simon Knight]

- Increment version. [Simon Knight]

- Use correct ip for update-source. [Simon Knight]

- Tidy anm sending over rabbit. [Simon Knight]

- Dev. [Simon Knight]

- Error handling alpha only name sorting. [Simon Knight]

- More visible traces. [Simon Knight]

- Updates for netkit deploy. [Simon Knight]

- Use rabbitmq server from config. [Simon Knight]

- Better log message. [Simon Knight]

- Fix int ids. [Simon Knight]

- Dev. [Simon Knight]

- Update version. [Simon Knight]

- Tidying. [Simon Knight]

- Tidying. [Simon Knight]

- Use package name. [Simon Knight]

- Get correct package name for version. [Simon Knight]

- Store original node label. [Simon Knight]

- Update ignore for package. [Simon Knight]

- Rename package version. [Simon Knight]

- Add console help, version. [Simon Knight]

- Remove dev. [Simon Knight]

- Adding directed input graph support - useful for edge attributes.
  [Simon Knight]

- Sort interfaces on id. [Simon Knight]

- Copy edge attributes. [Simon Knight]

- Edge comparisons for sorting. [Simon Knight]

- Improve bgp, isis. [Simon Knight]

- Better version string. [Simon Knight]

- Notes. [Simon Knight]

- Better ios support, isis. [Simon Knight]

- Default isis process id. [Simon Knight]

- Hide nav for printing. [Simon Knight]

- Longer delay for monitor, optional archiving, neater json writing for
  diff. [Simon Knight]

- Select between IGPs. [Simon Knight]

- Diffing support. [Simon Knight]

- Greatly improved differ. [Simon Knight]

- Ignore diff. [Simon Knight]

- Error message if no rabbitmq. [Simon Knight]

- Disable hardware alloc for now. [Simon Knight]

- Default dir. [Simon Knight]

- Testing diff. [Simon Knight]

- Handle sets. [Simon Knight]

- More on interfaces. [Simon Knight]

- Add graphics data. [Simon Knight]

- Setting group attr. [Simon Knight]

- Better error handling, retain of node id. [Simon Knight]

- Tidy. [Simon Knight]

- More dev. [Simon Knight]

- Basic interface icon. [Simon Knight]

- More testing for hw. [Simon Knight]

- Add remove_node fn. [Simon Knight]

- More hw alloc. [Simon Knight]

- Handle empty overlays. [Simon Knight]

- Adding conn graph. [Simon Knight]

- Graph based hardware. [Simon Knight]

- Change zoom. [Simon Knight]

- Group by device for conn graph. [Simon Knight]

- Add hash for set comparison, accessor for anm, option to add node,
  option to not clobber adding nodes, [Simon Knight]

- Before switching to graph-based interface representation. [Simon
  Knight]

- Hardware profiles. [Simon Knight]

- Tidy. [Simon Knight]

- Adding hardware profiles. [Simon Knight]

- Tidying. [Simon Knight]

- Adding standalone actions. [Simon Knight]

- Policy parsing implemented, including nested if/then/else. [Simon
  Knight]

- More policy. [Simon Knight]

- More pol. [Simon Knight]

- Initial policy parsing. [Simon Knight]

- Fix packaging. [Simon Knight]

- Handle imports better. [Simon Knight]

- Remove unused dep. [Simon Knight]

- Tidy. [Simon Knight]

- Tidy. [Simon Knight]

- Update. [Simon Knight]

- Updates. [Simon Knight]

- Disable sockets for now. [Simon Knight]

- Adding messaging. [Simon Knight]

- Update ignore. [Simon Knight]

- Add cisco internal support, tidy up, update build options if updated,
  relay update node parameter. [Simon Knight]

- Default disabled pika. [Simon Knight]

- Add node label, tidy. [Simon Knight]

- Relay update, support cisco internal host. [Simon Knight]

- Handle disabled pika. [Simon Knight]

- Restoring ios2. [Simon Knight]

- Update ignore. [Simon Knight]

- Exceptions class. [Simon Knight]

- Add sorting. [Simon Knight]

- Better exception handling. [Simon Knight]

- Add internal host. [Simon Knight]

- Handle non .graphml. [Simon Knight]

- Todo. [Simon Knight]

- Change sizes. [Simon Knight]

- Ignore. [Simon Knight]

- Remove. [Simon Knight]

- Tidying. [Simon Knight]

- Moved ip to be native networkx graph based. [Simon Knight]

- More tidying compiler. [Simon Knight]

- Keeping track of parent to update dicts. [Simon Knight]

- Nidb access methods needing work - can't modify dictionary accessors.
  [Simon Knight]

- Before updating interface format. [Simon Knight]

- Search by edge id. [Simon Knight]

- Append as kwargs. [Simon Knight]

- Moving to integrated lists. [Simon Knight]

- Tidy. [Simon Knight]

- Put in list (expected format) [Simon Knight]

- Don't clobber host attribute from switches bugfix. [Simon Knight]

- Adding sorting to tidy up compiler. [Simon Knight]

- Allocate ip not subnet to loopback. [Simon Knight]

- Add area back. [Simon Knight]

- Better vis, moving towards twitter bootstrap, scalable with resizing.
  [Simon Knight]

- Tidying formatting. [Simon Knight]

- Minimum of one rr per AS. [Simon Knight]

- Better transition from overlay -> ip allocs. [Simon Knight]

- Add node sorting for anm, placeholder for nidb. [Simon Knight]

- More ip progress. [Simon Knight]

- Ip addressing working. [Simon Knight]

- More ip. [Simon Knight]

- Add option to search for edge by node pair. [Simon Knight]

- Tidy. [Simon Knight]

- Use neighbors from overlay. [Simon Knight]

- Better ip vis. [Simon Knight]

- Testing radial layout. [Simon Knight]

- More addressing. [Simon Knight]

- More ip addressing. [Simon Knight]

- More ip addressing. [Simon Knight]

- Redoing IP allocation to be digraph (DAG) based. [Simon Knight]

- Better plotting. [Simon Knight]

- Transitions for updated ip data. [Simon Knight]

- Tidying, adding support for ip allocation plotting. [Simon Knight]

- Add demo to website. [Simon Knight]

- Remove debug. [Simon Knight]

- Remove debug. [Simon Knight]

- More config driven. [Simon Knight]

- Use standard folder format. [Simon Knight]

- Turn down base logging (fixes verbose paramiko) [Simon Knight]

- Tidy. [Simon Knight]

- Use config instead of hard-coded settings. [Simon Knight]

- Default boolean for general configs, add deploy hosts. [Simon Knight]

- Update title with revison number. [Simon Knight]

- Tidying igp. [Simon Knight]

- Move deploy to directory. [Simon Knight]

- Measure directory. [Simon Knight]

- More isis support. [Simon Knight]

- Ready for sorted. [Simon Knight]

- Debug on key miss. [Simon Knight]

- Retain data. [Simon Knight]

- Isis support. [Simon Knight]

- Ignore extra rendered. [Simon Knight]

- Subgraph only for netkit nodes. [Simon Knight]

- Remove defaults (use config) [Simon Knight]

- Tidy. [Simon Knight]

- Also load cisco compiler. [Simon Knight]

- Defaults from config. [Simon Knight]

- Defaults from config. [Simon Knight]

- More concise edge adding syntax. [Simon Knight]

- Debug. [Simon Knight]

- Tidy ip to network entity function. [Simon Knight]

- Use new graphml reader. [Simon Knight]

- Better most frequent algorithm. [Simon Knight]

- Split out graphml reader. [Simon Knight]

- Split out graphml reader, better most frequent algorithm. [Simon
  Knight]

- Create load module directory. [Simon Knight]

- Move to load module directory, remove old caching code. [Simon Knight]

- Add most frequent function, use instead. [Simon Knight]

- Use loopback to create network_entity_title. [Simon Knight]

- Bugfix: take most frequent ASN for inter-asn collision domains, rather
  than mean. [Simon Knight]

  (otherwise cd between ASN 2 and 4 gets put in 3)

- Add setup for pypi. [Simon Knight]

- Turn down log verbosity. [Simon Knight]

- Tidied, adding IS-IS support. [Simon Knight]

- Better file checking, tidied up building, better monitor mode,
  checking if build has changed, better stack trace. [Simon Knight]

- Ignore egg builds. [Simon Knight]

- Default overlay of phy not ospf. [Simon Knight]

- Bugfix: asn of parent not neighbor. [Simon Knight]

- Render for single run mode. [Simon Knight]

- Tidying. [Simon Knight]

- More descriptive queue name. [Simon Knight]

- Use server from config. [Simon Knight]

- Better formatting,zoom. [Simon Knight]

- Add zoom. [Simon Knight]

- Ignore local config, crash dump. [Simon Knight]

- Read from config. [Simon Knight]

- Default localhost. [Simon Knight]

- Default localhost. [Simon Knight]

- Hiding better layout for printing. [Simon Knight]

- Better layout. [Simon Knight]

- Fix fast-forward, add hidden option for printing each history
  revision. [Simon Knight]

- Update title with revision id. [Simon Knight]

- Added clarity for comparison. [Simon Knight]

- Add arrows, full history support. [Simon Knight]

- Use global config settings. [Simon Knight]

- Support for pika to update web ui. [Simon Knight]

- Add note. [Simon Knight]

- Revision back and forward. [Simon Knight]

- Also turn off infobar. [Simon Knight]

- Preselect correct dropdown based on overlay_id at init, add history
  support. [Simon Knight]

- Tidy print. [Simon Knight]

- Remove redundant code. [Simon Knight]

- Add print css to disable nav. [Simon Knight]

- Extra notes. [Simon Knight]

- Tidying js in vis. [Simon Knight]

- More tidying. [Simon Knight]

- Tidy. [Simon Knight]

- Add config file. [Simon Knight]

- Tidy. [Simon Knight]

- Serialize ip using json. [Simon Knight]

- Tidying. [Simon Knight]

- Default not to compile. [Simon Knight]

- Tidy json support. [Simon Knight]

- Use json instead of pickle for serializing anm. [Simon Knight]

- Function to copy graphics across from anm. [Simon Knight]

- Tidying compression, moving network construction to seperate module.
  [Simon Knight]

- Move network construction into seperate module. [Simon Knight]

- Abstract out pika messaging. [Simon Knight]

- Restore diffing (disabled for now awaiting stable IP addressing)
  [Simon Knight]

- Better error handling, initial support for diffs. [Simon Knight]

- Work with attributes rather than anm nodes directly. [Simon Knight]

- Handling nidb. [Simon Knight]

- Better serialization, de-serialize ip address/ip networks in lists
  properly. [Simon Knight]

- Don't use object references to anm nodes in nidb, use attributes eg
  asn, label, etc. [Simon Knight]

- Save/restore nidb using pickle. [Simon Knight]

- Directed edge arcs, working on arrow alignment. [Simon Knight]

- Trace colour. [Simon Knight]

- Plotting all traceroutes (bugfix) [Simon Knight]

- Loading saved json. [Simon Knight]

- Saving json. [Simon Knight]

- Testing cloud (doesn't scale width well) [Simon Knight]

- Add cloud icon. [Simon Knight]

- Set new default. [Simon Knight]

- Remove debug. [Simon Knight]

- Tweaking grouping. [Simon Knight]

- Grouping for single nodes, tidy. [Simon Knight]

- Add hull for groups of 2 nodes. [Simon Knight]

- Add compression for large anm that exceed rabbitmq max frame size.
  [Simon Knight]

- Add compression support. [Simon Knight]

- Add queue watching for debugging. [Simon Knight]

- Filter out incomplete traceroutes. [Simon Knight]

- Default not to compile. [Simon Knight]

- Increase dimensions. [Simon Knight]

- Tidy. [Simon Knight]

- Json handling IP address serialization and deserialization. [Simon
  Knight]

- Use json properly. [Simon Knight]

- Example to load on webserver. [Simon Knight]

- Send json not pickle to webserver. [Simon Knight]

- Update overlay dropdown, remove poll code. [Simon Knight]

- Tidy. [Simon Knight]

- Pass json over rabbitmq rather than pickled anm - much more flexible.
  [Simon Knight]

- Initial work to pass json anm rather than pickled anm across network
  to webserver. [Simon Knight]

- Create dir if needed for topology (bugfix) [Simon Knight]

- Extra todo note. [Simon Knight]

- Don't relabel if same label (saves clobbering node data) [Simon
  Knight]

- Visual tweaks, reload images -> stay vector. [Simon Knight]

- Placeholder. [Simon Knight]

- Ignore logs. [Simon Knight]

- Script to update website. [Simon Knight]

- Demo website redirect. [Simon Knight]

- Add pop to graphics. [Simon Knight]

- Smoother updates and transitions. [Simon Knight]

- Tidy debug. [Simon Knight]

- Visual tweaks. [Simon Knight]

- Handle if no version number. [Simon Knight]

- Problems with pika sending anm. [Simon Knight]

- Tidy. [Simon Knight]

- Better parsing and rmq messages on starting and launched. [Simon
  Knight]

- Nicer trace colours. [Simon Knight]

- Turn off compile by default. [Simon Knight]

- Handle paths. [Simon Knight]

- Add path for traceroutes. [Simon Knight]

- Fix traceroutes. [Simon Knight]

- Placeholder for webserver. [Simon Knight]

- Remove debug. [Simon Knight]

- Change status font, don't list id in attributes. [Simon Knight]

- Remove need for full ank install (better for remote servers) [Simon
  Knight]

- Tidy debug, better info messages. [Simon Knight]

- Add more icons. [Simon Knight]

- Websocket live updates working. [Simon Knight]

- Add rmq support. [Simon Knight]

- Debugging. [Simon Knight]

- Extra note. [Simon Knight]

- Moving to entirely websocket, no polling. [Simon Knight]

- Removing outdated webserver. [Simon Knight]

- Fix bug in monitoring. [Simon Knight]

- Better hull updates, status labels, general tidy, [Simon Knight]

- Better handling of no template attribute set. [Simon Knight]

- Fix grouping hulls. [Simon Knight]

- Update monitor mode. [Simon Knight]

- Better log output. [Simon Knight]

- Exception handling. [Simon Knight]

- Dynamic websocket url. [Simon Knight]

- Update label, select node from available nodes rather than hard-coded.
  [Simon Knight]

- Basic process error handling. [Simon Knight]

- Add support for http. [Simon Knight]

- Support tornado based web. [Simon Knight]

- Fix label naming, [Simon Knight]

- Moving webapp to single script, entirely in tornado. [Simon Knight]

- Don't run graph products if no template set. [Simon Knight]

- Remove debug. [Simon Knight]

- Remove debug. [Simon Knight]

- Graph products working. [Simon Knight]

- Remove debug. [Simon Knight]

- Remove debug. [Simon Knight]

- More graph products. [Simon Knight]

- More graph products. [Simon Knight]

- Plotting edges from graph products. [Simon Knight]

- Bug with hull in d3. [Simon Knight]

- Initial commit of graph products. [Simon Knight]

- Don't try overlays on first call. [Simon Knight]

- Adding graph product support. [Simon Knight]

- Bugfix. [Simon Knight]

- Fn to replace graph. [Simon Knight]

- Move icons. [Simon Knight]

- Tidying. [Simon Knight]

- Tidy icons. [Simon Knight]

- Tidying viz. [Simon Knight]

- More trace route parsing. [Simon Knight]

- Better trace route  vis. [Simon Knight]

- Neater save/restore. [Simon Knight]

- Turn down debug. [Simon Knight]

- Nidb save/restore. [Simon Knight]

- Visualize ip allocs. [Simon Knight]

- Tidy. [Simon Knight]

- Neater pickle. [Simon Knight]

- Path plotting in d3. [Simon Knight]

- More d3. [Simon Knight]

- More rabbitmq/json/websockets/d3. [Simon Knight]

- Bgp working, adding rmq sending of trace routes to d3. [Simon Knight]

- List machines in lab - don't just boot all folders. [Simon Knight]

- Log booting machines. [Simon Knight]

- Connect to interface not loopback ip for ebgp. [Simon Knight]

- Options for compile, deploy, measure. [Simon Knight]

- Add file logging. [Simon Knight]

- Fix issue where multiple threads create folder at same time. [Simon
  Knight]

- Use ethernet address for next-hop as workaround to DENIED due to: non-
  connected next-hop; [Simon Knight]

- Ebgp DENIED due to: non-connected next-hop. [Simon Knight]

- Add static loopback routes for bgp. [Simon Knight]

- Fix indent. [Simon Knight]

- Fix warning. [Simon Knight]

- Fix bgp network advertisement. [Simon Knight]

- Fixing ebgp for traceroutes. [Simon Knight]

- Adding extra measurement functions. [Simon Knight]

- End-to-end deployment using exscript, measurement using exscript/rmq,
  and parsing using textfsm. [Simon Knight]

- More rmq measurement. [Simon Knight]

- Adding rmq remote measurement. [Simon Knight]

- More textfsm. [Simon Knight]

- With initial textfsm processing of sh ip route. [Simon Knight]

- Trying to capture routing output using exscript templates. [Simon
  Knight]

- Collecting data from hosts. [Simon Knight]

- Fixing bgp config. [Simon Knight]

- Fixing netkit routing. [Simon Knight]

- Use remote interface ip for eBGP not loopback. [Simon Knight]

- Fix issue with single dst node being treated as string for set. [Simon
  Knight]

- More netkit deploy improvements. [Simon Knight]

- Fixing netkit deployment. [Simon Knight]

- Remove previous lab dirs. [Simon Knight]

- Testing deployment. [Simon Knight]

- Testing. [Simon Knight]

- Better deployment. [Simon Knight]

- Don't save ip allocs -> speed. [Simon Knight]

- Fix up naming. [Simon Knight]

- Recommit. [Simon Knight]

- Update ignore. [Simon Knight]

- Better formatting. [Simon Knight]

- Support host keys. [Simon Knight]

- Use nklab not netkit as  folder, support for host keys. [Simon Knight]

- Add nonzero for nodes, fix subtle issue with evaluation nonzero for
  None values in nidb_node_category. [Simon Knight]

- Update template names. [Simon Knight]

- Pass Network name to nidb. [Simon Knight]

- Sort rendering. [Simon Knight]

- Default name handling. [Simon Knight]

- Ignore graphmls. [Simon Knight]

- Tidying, add ssh. [Simon Knight]

- Copy Network for zoo graphs. [Simon Knight]

- New function to copy attributes from one overlay to another. [Simon
  Knight]

- Remove debug. [Simon Knight]

- Different folder naming structure. [Simon Knight]

- Dump graph attributes. [Simon Knight]

- New naming functions. [Simon Knight]

- Fixes. [Simon Knight]

- Writing collision domains. [Simon Knight]

- Update ignore. [Simon Knight]

- Remove built docs. [Simon Knight]


