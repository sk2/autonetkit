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
    settings = ConfigParser.RawConfigParser()
    spec_file = pkg_resources.resource_filename(__name__,"/config/configspec.cfg")
    settings = ConfigObj(configspec=spec_file, encoding='UTF8')
# User's ANK settings
    user_config_file = os.path.join(ank_user_dir, "autonetkit.cfg")
    settings.merge(ConfigObj(user_config_file))
# ANK settings in current directory
    settings.merge(ConfigObj("autonetkit.cfg"))
# ANK settings specified by environment variable
    try:
        ankcfg = os.environ['AUTONETKIT_CFG']
        settings.merge(ConfigObj(ankcfg))
    except KeyError:
        pass

    results = settings.validate(validator)
    if results != True:
        for (section_list, key, _) in flatten_errors(settings, results):
            if key is not None:
                print "Error loading configuration file:"
                print 'Invalid key "%s" in section "%s"' % (key, ', '.join(section_list))
                raise AutoNetkitException
            else:
# ignore missing sections - use defaults
                #print 'The following section was missing:%s ' % ', '.join(section_list)
                pass
    return settings

#NOTE: this only gets loaded once package-wide if imported as import autonetkit.config
settings = load_config()
