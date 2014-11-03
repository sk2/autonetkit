import ConfigParser
import os
import os.path

import pkg_resources
import validate
from autonetkit.exception import AutoNetkitException
from configobj import ConfigObj, flatten_errors

validator = validate.Validator()

# from http://stackoverflow.com/questions/4028904
ank_user_dir = os.path.join(os.path.expanduser("~"),  ".autonetkit")

def load_config():
    retval = ConfigParser.RawConfigParser()
    spec_file = pkg_resources.resource_filename(__name__,"/config/configspec.cfg")
    retval = ConfigObj(configspec=spec_file, encoding='UTF8')
# User's ANK retval
    user_config_file = os.path.join(ank_user_dir, "autonetkit.cfg")
    retval.merge(ConfigObj(user_config_file))
# ANK retval in current directory
    retval.merge(ConfigObj("autonetkit.cfg"))
# ANK retval specified by environment variable
    try:
        ankcfg = os.environ['AUTONETKIT_CFG']
        retval.merge(ConfigObj(ankcfg))
    except KeyError:
        pass

    results = retval.validate(validator)
    if results != True:
        for (section_list, key, _) in flatten_errors(retval, results):
            if key is not None:
                print "Error loading configuration file:"
                print 'Invalid key "%s" in section "%s"' % (key, ', '.join(section_list))
                raise AutoNetkitException
            else:
# ignore missing sections - use defaults
                #print 'The following section was missing:%s ' % ', '.join(section_list)
                pass
    return retval

#NOTE: this only gets loaded once package-wide if imported as import autonetkit.config
settings = load_config()
