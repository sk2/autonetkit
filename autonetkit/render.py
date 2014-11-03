import fnmatch
import os
import shutil
import time

import autonetkit.log as log
import mako
import pkg_resources
from mako.exceptions import SyntaxException
from mako.lookup import TemplateLookup

# TODO: have same error handling block for each template render call

# TODO: clean up cache enable/disable


def resource_path(relative):
    """Makes relative to package"""
    return pkg_resources.resource_filename(__name__, relative)

# TODO: fix support here for template lookups, internal, user provided
#template_cache_dir = config.template_cache_dir
template_cache_dir = "cache"

# disable cache for cleaner folder structure


def initialise_lookup():
    retval = TemplateLookup(directories=[resource_path("")],
                            #module_directory= template_cache_dir,
                            cache_type='memory',
                            cache_enabled=True,
                            )

    try:
        cisco_templates = pkg_resources.resource_filename(
            "autonetkit_cisco", "")
        retval.directories.append(cisco_templates)
    except ImportError:
        pass  # Cisco ANK not present

    # and cwd
    retval.directories.append(os.getcwd())

    return retval

# TODO: make lookup initialised once rather than global for module import
# and allow users to append to the lookup
TEMPLATE_LOOKUP = initialise_lookup()

try:
    from autonetkit_cisco.template_wrapper import inject_templates
    inject_templates(TEMPLATE_LOOKUP)
except ImportError:
    pass


def format_version_banner():
    version_banner = "autonetkit_dev"
    try:
        # test if can import, if not present will fail and not add to template
        # path
        import autonetkit_cisco
    except ImportError:
        pass
    else:
        import autonetkit_cisco.version
        version_banner = autonetkit_cisco.version.banner()
        return version_banner

    try:
        version_banner = ("autonetkit_%s" %
                          pkg_resources.get_distribution("autonetkit").version)
        # TODO: pick up name automatically
    except pkg_resources.DistributionNotFound:
        version_banner = "autonetkit_dev"

    return version_banner

# TODO: make a render class, that caches traversed folders for speed


def render_inline(node, render_template_file, to_memory=True,
                  render_dst_file=None):
    """Generic rendering of a node attribute rather than the standard location.
    Needs to be called by render_node.
    Doesn't support base folders - only single attributes.
    Note: supports rendering to memory (ie back to nidb rather than file)
    """

    node.log.debug("Rendering template %s" % (render_template_file))
    version_banner = format_version_banner()

    date = time.strftime("%Y-%m-%d %H:%M", time.localtime())

    if render_template_file:
        try:
            render_template = TEMPLATE_LOOKUP.get_template(
                render_template_file)
        except SyntaxException, error:
            log.warning("Unable to render %s: "
                        "Syntax error in template: %s" % (node, error))
            return

        if to_memory:
            # Render directly to DeviceModel
            render_output = render_template.render(
                node=node,
                version_banner=version_banner,
                date=date,
            )

            return render_output

# TODO: Add support for both src template and src folder (eg for quagga,
# servers)


def render_node(node):
    if not node.do_render:
        node.log.debug("Rendering disabled for node")
        return

    try:
        render_output_dir = node.render.dst_folder
        # TODO: could check if base is set, so don't put error into debug log
        render_base = node.render.base
        render_base_output_dir = node.render.base_dst_folder
        render_template_file = node.render.template
        render_custom = node.render.custom
    except KeyError, error:
        # TODO: make sure allows case of just custom render
        return

    version_banner = format_version_banner()

    date = time.strftime("%Y-%m-%d %H:%M", time.localtime())
    if render_custom:
        # print render_custom
        pass

# TODO: make sure is an abspath here so don't wipe user directory!!!
    if render_output_dir and not os.path.isdir(render_output_dir):
        try:
            os.makedirs(render_output_dir)
        except OSError, e:
            if e.strerror == "File exists":
                pass  # created by another process, safe to ignore
            else:
                raise e

    if render_template_file:
        try:
            render_template = TEMPLATE_LOOKUP.get_template(
                render_template_file)
        except SyntaxException, error:
            log.warning("Unable to render %s: "
                        "Syntax error in template: %s" % (node, error))
            return

        if node.render.dst_file:
            dst_file = os.path.join(render_output_dir, node.render.dst_file)
            with open(dst_file, 'wb') as dst_fh:
                try:
                    dst_fh.write(render_template.render(
                        node=node,
                        version_banner=version_banner,
                        date=date,
                    ))
                except KeyError, error:
                    log.warning("Unable to render %s:"
                                " %s not set" % (node, error))
                    from mako import exceptions
                    log.debug(exceptions.text_error_template().render())
                except AttributeError, error:
                    log.warning("Unable to render %s: %s " % (node, error))
                    from mako import exceptions
                    log.debug(exceptions.text_error_template().render())
                except NameError, error:
                    log.warning("Unable to render %s: %s. "
                                "Check all variables used are defined" % (node, error))
                except TypeError, error:
                    log.warning("Unable to render %s: %s." % (node, error))
                    from mako import exceptions
                    log.debug(exceptions.text_error_template().render())

        if node.render.to_memory:
            # Render directly to DeviceModel
            node.render.render_output = render_template.render(
                node=node,
                version_banner=version_banner,
                date=date,
            )

    if render_base:
        # TODO: revert to shutil copy
        if render_base:
            render_base = resource_path(render_base)
            fs_mako_templates = []
            for root, _, filenames in os.walk(render_base):
                for filename in fnmatch.filter(filenames, '*.mako'):
                    # relative to fs root
                    rel_root = os.path.relpath(root, render_base)
                    fs_mako_templates.append(os.path.join(rel_root, filename))

            try:
                shutil.rmtree(render_base_output_dir)
            except OSError:
                pass  # doesn't exist
            shutil.copytree(render_base, render_base_output_dir,
                            ignore=shutil.ignore_patterns('*.mako'))
            for template_file in fs_mako_templates:
                template_file_path = os.path.normpath(
                    os.path.join(render_base, template_file))
                mytemplate = mako.template.Template(filename=template_file_path,
                                                    )
                dst_file = os.path.normpath(
                    (os.path.join(render_base_output_dir, template_file)))
                dst_file, _ = os.path.splitext(dst_file)  # remove .mako suffix
                with open(dst_file, 'wb') as dst_fh:
                    dst_fh.write(mytemplate.render(
                        node=node,
                        version_banner=version_banner,
                        date=date,
                    ))
        return


def render(nidb):
    # TODO: config option for single or multi threaded
    log.debug("Rendering Configuration Files")
    render_single(nidb)
    render_topologies(nidb)


def render_single(nidb):
    for node in sorted(nidb):
        render_node(node)


def render_topologies(nidb):
    for topology in nidb.topologies():
        render_topology(topology)


def render_topology(topology):
    version_banner = format_version_banner()

    date = time.strftime("%Y-%m-%d %H:%M", time.localtime())
    try:
        render_output_dir = topology.render_dst_folder
        render_template_file = topology.render_template
    except KeyError, error:
        return

    if not render_template_file:
        log.debug("No render template specified for topology %s, skipping"
                  % topology)
        return

    try:
        render_template = TEMPLATE_LOOKUP.get_template(render_template_file)
    except SyntaxException, error:
        log.warning(
            "Unable to render %s: Syntax error in template: %s" % (topology, error))
        return

    if not os.path.isdir(render_output_dir):
        try:
            os.makedirs(render_output_dir)
        except OSError, e:
            # TODO: replace with e.errno
            if e.strerror == "File exists":
                pass  # created by another process, safe to ignore
            else:
                raise e
    dst_file = os.path.join(render_output_dir, topology.render_dst_file)

# TODO: may need to iterate if multiple parts of the directory need to be
# created

    # TODO: capture mako errors better

    with open(dst_file, 'wb') as dst_fh:
        try:
            dst_fh.write(render_template.render(
                topology=topology,
                version_banner=version_banner,
                date=date,
            ))
        except KeyError, error:
            log.warning("Unable to render %s: %s not set" % (topology, error))
        except AttributeError, error:
            log.warning("Unable to render %s: %s " % (topology, error))
        except NameError, error:
            log.warning("Unable to render %s: %s. Check all variables used are defined" % (
                topology, error))
        except TypeError, error:
            log.warning("Unable to render topology: %s." % (error))
            from mako import exceptions
            log.warning(exceptions.text_error_template().render())
