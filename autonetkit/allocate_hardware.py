import pkg_resources
import validate
import ConfigParser
from configobj import ConfigObj, flatten_errors
import configobj
validator = validate.Validator()
import os.path
import pprint

#Note: configspec preserves order: configobj.Sections which behave as a dict, but retain order specified in - allows precedence based on ordering in specification file

def InterfaceGenerator(interfaces):
    """Forms a tree of subinterfaces"""
    #for interface in interfaces:
    #    for x in interface:
    #        print "x is", x
    pass

class Interface(object):
    def __init__(self, ):
        self.data = kwargs

class HardwareProfile(object):
    def __init__(self, data):
# map the data from the loaded config
        self.name = data[0] # data is a tuple of (key, values)
        values = data[1]
        return
        interfaces = [(int_name, int_data) for (int_name, int_data) in values.items() 
                if int_name != "System"] # all the rest
        #print interfaces

        test = InterfaceGenerator(interfaces)
        #print test

#TODO: do string matching to see if generator in list of reserved... ie taken interfaces

        self.interface_generator = self.build_interfaces()


    def build_interfaces(self):
# sets an internal generator for interfaces
        for x in range(3):
            for y in range(5):
                yield "%s.%s" % (x, y)

        for x in range(5):
            yield x
        for x in range(12):
            yield x

    def next_interface(self):
        return self.interface_generator.next()

    def __repr__(self):
        return "Profile: %s" % self.name

def load_profiles():
    settings = ConfigParser.RawConfigParser()
    spec_file = pkg_resources.resource_filename(__name__,"/hardware_profiles/spec.cfg")
    settings = ConfigObj(configspec=spec_file, encoding='UTF8')
    default_profile = pkg_resources.resource_filename(__name__,"/hardware_profiles/default.cfg")
    settings.merge(ConfigObj(default_profile))

    #results = settings.validate(validator)
    #if results != True:
        #for (section_list, key, _) in flatten_errors(settings, results):
            #if key is not None:
                #print "Error loading configuration file:"
                #print 'Invalid key "%s" in section "%s"' % (key, ', '.join(section_list))
                #raise SystemExit
            #else:
# ignore missing sections - use defaults
                #print 'The following section was missing:%s ' % ', '.join(section_list)
                #pass

    profiles = []
    for data in settings.items():
        profiles.append(HardwareProfile(data))

# walk to return tree of interfaces, subinterfaces, etc
    def walker(section, key):
        val = section[key]
        if isinstance(val, configobj.Section): #TODO: filter on depth > 1 otherwise get bases... if depth == 1 then this is a hardwareprofile class if any greater then is a interface
            print section.name, "is section", section
#TODO: also check type of section? eg for subeth?? - this would then have the data as a dict... and then hand this off tp the interface object, and skip any others for this section... which are the individual values
        print section.depth, section.name,  key, type(section), val, type(val)
        return
# skip system
        if section.depth == 1:
            print "here for ", section.name, key
            return "CCC"
            return "Platform: %s" % section.name
        if section.depth == 2 and section.name == "System":
            #print "skip system"
            return
        print "parent", section.parent.name, type(section)
        print "Subsection", section.depth, section.name, key
        print
        return "AA"

#TODO: Note this doesn't replace the parent.... which is what would be ideal for quickly building structure (like pyparsing does)
# but does as a dict, so can traverse the dict easily (build recursive walker)
    res = settings.walk(walker, call_on_sections=True)
    pprint.pprint(res)
    return

    for name in settings:
        print name
        res = settings[name].walk(walker)
        print res



    return profiles

    

def allocate(G_phy):

    profiles = load_profiles()
    return
    for profile in profiles:
        print profile
        for i in range(20):
            print profile.next_interface()
            pass

    raise SystemExit
