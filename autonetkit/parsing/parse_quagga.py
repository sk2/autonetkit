import pprint

from pyparsing import (alphanums, alphas, Combine, Dict, Each, Group,
                       indentedBlock, Literal, nums, OneOrMore, Optional, Or,
                       Suppress, SkipTo,
                       restOfLine, Word, ZeroOrMore)

from collections import defaultdict

def fn_interface(strg, loc, toks):
    data = toks.asDict()
    #print "here for", data['id']

    retval = {"id" : data.get("id")}
    if data.get("indent"):
        indent = data.get('indent', [])[0]
        retval['ip'] = indent.get('ip address', {}).get("ip", None)
        retval['description'] = indent.get('description', {}).get("description", None)
        retval['ospf cost'] = indent.get('ospf cost', {}).get("cost", None)

    return retval

def fn_ospf(strg, loc, toks):
    data = toks
    networks = []
    for elem in data.networks:
       network = elem.network
       area = elem.area
       networks.append({'network': network, 'area': area})

    return {
       'networks': networks,
   }

def fn_bgp(strg, loc, toks):
    data = toks.asDict()
    #print data.get("synchronization")
    #print data.get("networks")

    neighbors = data.get("neighbors")
    neigh_data = []
    for elem in neighbors:
        #print elem.dump()
        neighbor = elem.get("remote-as").get("neighbor")
        asn = elem.get("remote-as").get("asn")
        update_source = bool(elem.get("update-source", False))
        send_commmunity = bool(elem.get("send-commmunity", False))
        neigh_data.append({
        'neighbor': neighbor,
        'asn': asn,
        'update-source': update_source,
        'send-commmunity': send_commmunity
        })


#TODO: return router-id etc

    return {
    'neighbors': neigh_data,
    }


#TODO: need naming convention for primitives and config lines

indentStack = [1]

ipV4Address = Combine(Word(nums) + ('.' + Word(nums))*3)
ipv4_prefixlen = Word(nums, min=1, max=2)
# fix this - combine?
ipAddressWithMask = Combine(Word(nums) + ('.' + Word(nums))*3 + "/" + ipv4_prefixlen)
integer = Word(nums)
comment = Group("!" + restOfLine)
hash_comment = Group("#" + restOfLine)

router_id = (ipV4Address | integer)
word_param  = Word(alphanums)
interface_id  = Word(alphanums + ":")

#TODO: make function to return thesline_ip_addresse
password = "password" + word_param
enable_password = "enable password" + word_param
banner_motd = "banner motd " + word_param("type") + restOfLine("path")


line_ip_address = "ip address" + ipAddressWithMask("ip")
line_description = "description" + restOfLine("description")
line_ip_ospf_cost = "ip ospf cost" + integer("cost")

interface_properties = OneOrMore(
    line_ip_address("ip address") |
    line_description("description") |
    line_ip_ospf_cost("ospf cost") |
    comment|
    hash_comment
    )

interface_indent = indentedBlock(interface_properties, indentStack, True)("indent")
interface_id = "interface" + interface_id("id")

interface = ( interface_id + Optional(interface_indent)).setParseAction(fn_interface)
interfaces = OneOrMore(interface.setResultsName("interface", listAllMatches=True))


#### BGP
#TODO: put each protocol stanza into a function - variable scope, etc
router_bgp = "router bgp" + integer("asn")

#TODO: can router-id be an integer too?

#false_no: returns False if "no" is present, otherwise returns True
false_no = Optional(Literal("no").setParseAction(lambda x: False), default = True)
#bgp_synchronization = Optional(false_no, default =True) + "synchronization"
bgp_synchronization = false_no("synchronization") + "synchronization"

bgp_network = Group("network" + ipAddressWithMask("network"))
bgp_networks = OneOrMore(bgp_network)("networks")

def true_if_set(param):
    """returns true if param set"""
    return Literal(param).setParseAction(lambda s, l, t: bool(t[0]))


# in Pyparsing & means matching can be done in any order
"""
TODO: this will only work if the neighbors are grouped together - is that sufficient for configs?
or can we assume that they will be ordered if output from the router
"""

bgp_neighbor = Group(
    ("neighbor" + ipV4Address("neighbor") + "remote-as" + integer("asn"))("remote-as")
    &
    Optional("neighbor" + ipV4Address("neighbor") + "update-source" + ipV4Address("update-source"))("update-source")
    &
    Optional("neighbor" + ipV4Address("neighbor") + true_if_set("send-community"))("send-community")
    &
    Optional("neighbor" + ipV4Address("neighbor") + true_if_set("next-hop-self"))("next-hop-self")
    )

neighbors = OneOrMore(
    bgp_neighbor.setResultsName("neighbor", listAllMatches=True)
    |
    Suppress(comment)
    #)("neighbors")
    ).setResultsName("neighbors")

bgp_indent = OneOrMore(
    ("bgp router-id" + router_id("router-id"))("router-id") |
    bgp_synchronization
    | bgp_networks
    | comment
    | neighbors
    )

bgp_stanza = (router_bgp + bgp_indent).setParseAction(fn_bgp)("bgp")

#### OSPF
process_id = (integer | ipV4Address)
ospf_area = (integer | ipV4Address)
router_ospf = "router ospf" + Optional(process_id)("process_id")

ospf_network =Group("network" + ipAddressWithMask("network") + "area" + ospf_area("area"))
ospf_networks = OneOrMore(ospf_network)("networks")

passive_interface = Group("passive-interface" + interface_id("id"))
passive_interfaces = OneOrMore(passive_interface)("passive_interfaces")

#ipAddressWithMask
ospf_indent = OneOrMore(
    ospf_networks |
    comment |
    passive_interfaces
    )

ospf_stanza = (router_ospf + ospf_indent).setParseAction(fn_ospf)("ospf")



## putting together

preamble = OneOrMore(password("password") |
enable_password("enable_password") |
banner_motd("banner_motd")  )

no_command = Group("no" + restOfLine)

#TODO: work out why ZeroOrMore hangs
other_commands = OneOrMore(Literal("redundancy") |  "test" |
    no_command)

#Note this is done in order?
elements = (
    preamble &
    interfaces("interfaces") &
    OneOrMore(other_commands) &
    bgp_stanza &
    OneOrMore(comment) &
    ospf_stanza
    )


parser = elements

result =  parser.parseFile("quagga.conf")
#pprint.pprint(result.asDict())


#print result.dump()


pprint.pprint(result.bgp)

pprint.pprint(result.bgp)
raise SystemExit

print result[0].asDict()
result = result[0].asDict()

print result

interfaces = result["interfaces"]
for interface in result['interfaces']:
    print interface

#print "bgp", pprint.pprint(result["bgp"])
print "ospf", pprint.pprint(result["ospf"])


import pprint
pprint.pprint(result)
