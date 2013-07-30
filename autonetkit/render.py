import mako
from mako.lookup import TemplateLookup
from mako.exceptions import SyntaxException
import os
import threading
import Queue
import time
import shutil
import fnmatch
import pkg_resources
import autonetkit.log as log

#TODO: clean up cache enable/disable

def resource_path(relative):
    """Makes relative to package"""
    return pkg_resources.resource_filename(__name__, relative)

#TODO: fix support here for template lookups, internal, user provided
#template_cache_dir = config.template_cache_dir
template_cache_dir = "cache"

#disable cache for cleaner folder structure

#TODO: Also try for Cisco build here

lookup = TemplateLookup(directories=[resource_path("")],
                        #module_directory= template_cache_dir,
                        cache_type='memory',
                        cache_enabled=True,
                       )

try:
    import autonetkit_cisco # test if can import, if not present will fail and not add to template path
    cisco_templates = pkg_resources.resource_filename("autonetkit_cisco", "")
    lookup.directories.append(cisco_templates)
except ImportError:
    pass # Cisco ANK not present

#TODO: make a render class, that caches traversed folders for speed

#TODO: Add support for both src template and src folder (eg for quagga, servers)
def render_node(node, folder_cache):
    log.debug("Rendering %s" % node)
    try:
        render_output_dir = node.render.dst_folder
        #TODO: could check if base is set, so don't put error into debug log
        render_base = node.render.base
        render_base_output_dir = node.render.base_dst_folder
        render_template_file = node.render.template
        render_custom = node.render.custom
    except KeyError, error:
        #TODO: make sure allows case of just custom render
        return

    try:
        ank_version = ("autonetkit_%s" %
            pkg_resources.get_distribution("autonetkit").version)
         #TODO: pick up name automatically
    except pkg_resources.DistributionNotFound:
        ank_version = "autonetkit_dev"

    date = time.strftime("%Y-%m-%d %H:%M", time.localtime())
    if render_custom:
        #print render_custom
        pass

#TODO: make sure is an abspath here so don't wipe user directory!!!
    if render_output_dir and not os.path.isdir(render_output_dir):
        try:
            os.makedirs(render_output_dir)
        except OSError, e:
            if e.strerror == "File exists":
                pass # created by another process, safe to ignore
            else:
                raise e


    if render_template_file:
        try:
            render_template = lookup.get_template(render_template_file)
        except SyntaxException, error:
            log.warning( "Unable to render %s: "
                "Syntax error in template: %s" % (node, error))
            return

        if node.render.dst_file:
            dst_file = os.path.join(render_output_dir, node.render.dst_file)
            with open( dst_file, 'wb') as dst_fh:
                try:
                    dst_fh.write(render_template.render(
                        node = node,
                        ank_version = ank_version,
                        date = date,
                        ))
                except KeyError, error:
                    log.warning( "Unable to render %s:"
                        " %s not set" % (node, error))
                except AttributeError, error:
                    log.warning( "Unable to render %s: %s " % (node, error))
                    from mako import exceptions
                    log.warning(exceptions.text_error_template().render())
                except NameError, error:
                    log.warning( "Unable to render %s: %s. "
                        "Check all variables used are defined" % (node, error))
                except TypeError, error:
                    log.warning( "Unable to render %s: %s." % (node, error))
                    from mako import exceptions
                    log.warning(exceptions.text_error_template().render())


        if node.render.to_memory:
# Render directly to NIDB
            node.render.render_output = render_template.render(
                        node = node,
                        ank_version = ank_version,
                        date = date,
                        )
    if render_base:
        if render_base in folder_cache:
            src_folder = folder_cache[render_base]['folder']
            fs_mako_templates = folder_cache[render_base]['templates']

            try:
                shutil.rmtree(render_base_output_dir)
            except OSError:
                pass # doesn't exist
            shutil.copytree(src_folder, render_base_output_dir)

            for template_file in fs_mako_templates:
                render_base_rel = resource_path(render_base)
                template_file_path = os.path.normpath(os.path.join(render_base_rel,
                    template_file))
                mytemplate = mako.template.Template(filename=template_file_path,
# disabled cache
#module_directory= mako_tmp_dir
                        )
                dst_file = os.path.normpath((os.path.join(render_base_output_dir, template_file)))
                dst_file, _ = os.path.splitext(dst_file) # remove .mako suffix
                with open( dst_file, 'wb') as dst_fh:
                    dst_fh.write(mytemplate.render(
                        node = node,
                        ank_version = ank_version,
                        date = date,
                        ))
            return

def cache_folders(nidb):
    #TODO: see if this is required, revert to old renderer?
    #TODO: look at copying to clobber folders rather than shutil remove
    import tempfile
    render_base = {node.render.base for node in nidb}
    folder_cache_dir = tempfile.mkdtemp()
    try:
        render_base.remove(None)
    except KeyError:
        pass # Not present

    folder_cache = {}
    folder_cache['_folder_cache_dir'] = folder_cache_dir

    for base in render_base:
        folder_list = []
        full_base = resource_path(base)
        base_cache_dir = os.path.join(folder_cache_dir, base)
        shutil.copytree(full_base, base_cache_dir,
                ignore=shutil.ignore_patterns('*.mako'))

        fs_mako_templates = []
        for root, _, filenames in os.walk(full_base):
            rel_root = os.path.relpath(root, full_base) # relative to fs root
            folder_list.append(rel_root)
            mako_templates = {f for f in filenames if f.endswith(".mako")}
            for filename in mako_templates:
                fs_mako_templates.append(os.path.join(rel_root, filename))

#TODO: push templates into a cache dir

        folder_cache[base] = {
                'folder': base_cache_dir,
                'templates': fs_mako_templates,
                'folder_list': folder_list,
                }

    return folder_cache


def render(nidb):
    #TODO: config option for single or multi threaded
    log.info("Rendering Network")
    folder_cache = cache_folders(nidb)
    render_single(nidb, folder_cache)
    render_topologies(nidb)

#TODO: Also cache for topologies

    folder_cache_dir = folder_cache['_folder_cache_dir']
    shutil.rmtree(folder_cache_dir)


def render_single(nidb, folder_cache):
    for node in sorted(nidb):
        render_node(node, folder_cache)

def render_topologies(nidb):
    for topology in nidb.topology:
        render_topology(topology)

def render_topology(topology):
    try:
        ank_version = "autonetkit_%s" % pkg_resources.get_distribution("autonetkit").version #TODO: pick up name automatically
    except pkg_resources.DistributionNotFound:
        ank_version = "autonetkit_dev"
    date = time.strftime("%Y-%m-%d %H:%M", time.localtime())
    try:
        render_output_dir = topology.render_dst_folder
        render_base = topology.render_base
        render_base_output_dir = topology.render_base_dst_folder
        render_template_file = topology.render_template
    except KeyError, error:
        return

    if not render_template_file:
        log.debug("No render template specified for topology %s, skipping"
                % topology)
        return

    try:
        render_template = lookup.get_template(render_template_file)
    except SyntaxException, error:
        log.warning("Unable to render %s: Syntax error in template: %s" % (topology, error))
        return


    if not os.path.isdir(render_output_dir):
        try:
            os.makedirs(render_output_dir)
        except OSError, e:
            #TODO: replace with e.errno
            if e.strerror == "File exists":
                pass # created by another process, safe to ignore
            else:
                raise e
    dst_file = os.path.join(render_output_dir, topology.render_dst_file)

#TODO: may need to iterate if multiple parts of the directory need to be created

    #TODO: capture mako errors better

    with open( dst_file, 'wb') as dst_fh:
        try:
            dst_fh.write(render_template.render(
                topology = topology,
                ank_version = ank_version,
                date = date,
                ))
        except KeyError, error:
            log.warning( "Unable to render %s: %s not set" % (topology, error))
        except AttributeError, error:
            log.warning( "Unable to render %s: %s " % (topology, error))
        except NameError, error:
            log.warning( "Unable to render %s: %s. Check all variables used are defined" % (topology, error))
        except TypeError, error:
            log.warning( "Unable to render topology: %s." % (error))
            from mako import exceptions
            log.warning(exceptions.text_error_template().render())


