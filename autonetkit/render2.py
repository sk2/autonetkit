from collections import defaultdict
import os
import autonetkit.log as log


# TODO: need to work out clean way to handle template searchspaces
# and to allow users to specify their own templates from disk, or own
# searchspaces?

# TODO: need to implement caching for performance

from collections import namedtuple
src_dst = namedtuple("src_dst", ['src', 'dst'])


class NodeRender(object):

    def __init__(self, files=None, folders=None):
        self._files = defaultdict(list)
        self._folders = defaultdict(list)
        # TODO: need a new dict for each pass_id to store if memory/file... or just do all to memory?
        # and then platform decides the output
        for filename in files or []:
            self.add_file(filename)
        for foldername in files or []:
            self.add_folder(foldername)

    def __iter__(self):
        """Returns each render pass as a namedtuple of structure:

        with the folder structure flattened out to a list
        to_disk is default of False (render to memory by default)
        """
        pass

    def add_template_location(self, location):
        """TODO: allow user to specify a location to search
        """
        pass

    # TODO:implement __add__ with defaults for add_file

    # TODO: take in location (by default is autonetkit templates dir)
    def add_file(self, src, dst=None, pass_id=0):
        """Adds a file to pass "pass"
        dst is the target filename, if not set the src is used
        """
        if dst is None:
            dst = src
        self._files[pass_id].append(src_dst(src, dst))

    def add_folder(self, src, dst=None, pass_id=0):
        """Pass in folder as a list, will automatically apply os.path.sep"""
        if dst is None:
            dst = src
        self._folders[pass_id].append(src_dst(src, dst))

    def to_json(self):
        # TODO: return folders then files
        return {'files': self._files, 'folders': self._folders}

    def flatten(self):
        # flattens nested dicts out
        pass

    def get_files(self, pass_id=0):
        return self._files.get(pass_id)

    def get_file_dst(self, src, pass_id=0):
        return self._files.get(pass_id).get(src)

    def get_folders(self, pass_id=0):
        return self._folders.get(pass_id)


class PlatformRender(NodeRender):

    def __init__(self):
        super(PlatformRender, self).__init__()
        self.nodes = []
        self.base_folder = ""
        self.archive = None
        self.template_data = {}

    def add_node(self, node):
        self.nodes.append(node)

    def to_json(self):
        return self.nodes

    def __iter__(self):
        return iter(self.nodes)


def setup():
    # any setup steps for renderers
    pass


def render_node(node):
    pass


def render_topology_basic(topology):
    """Simple renderer, no caching"""
    for node in topology.render2:
        print node


# TODO: Put inside class once created
# TODO: inherit from common base

class MakoRenderer(object):

    def __init__(self):
        # if archive is none then render to memory
        # Note: this could also include setting lookup directories (unlikely to
        # be required though)
        pass

    def prepare(self, template_data):
        from mako.template import Template
        return Template(template_data)

    def render(self, template, node, version_banner, date, template_data=None):
        if template_data is None:
            template_data = {}

        try:
            return template.render(
                node=node,
                version_banner=version_banner,
                date=date,
                **template_data
            )
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

        import ipdb
        ipdb.set_trace()


def get_folder_contents(folder):
    retval = []

    for base, _, filenames in os.walk(folder):
        for name in filenames:
            # TODO: take in a skiplist
            if name == ".DS_Store":
                continue
            # TODO: see if can iterate folder?
            file_base = base.replace(folder, "")
            file_base = file_base[1:]  # strip leading /
            retval.append(os.path.join(file_base, name))

    return retval

extension_renderers = {'.mako': MakoRenderer()}


def render_nodes(nodes, base_folder="",
                 archive=None):

    if archive is None:
        to_memory = True
    else:
        to_memory = False

    # extracts common paths from the nodes
    # first build up list of all paths
    common_files = defaultdict(list)
    common_folders = defaultdict(list)

    if isinstance(base_folder, basestring):
        pass
    else:
        base_folder = os.path.join(*base_folder)

    # store destinations
    file_dsts = defaultdict(dict)
    folder_dsts = defaultdict(dict)

    for node in nodes:
        # print node.render2.get_pass()
        # TODO: need to iterate over all passes
        for path in node.render2.get_files():
            src = tuple(path.src)
            common_files[src].append(node)
            file_dsts[node][src] = path.dst
        # TODO: need to skip templates..... defined programatically in mapping
        # TODO: probably need to make a render class for this...
        for path in node.render2.get_folders():
            src = tuple(path.src)
            common_folders[src].append(node)
            folder_dsts[node][src] = path.dst

    # print common_files
    # print common_folders

    # load common files into cache
    # TODO: no cache now do file-by-file
    # TODO: do folders first so more specific precedence over less specific
    # in case of a clash (like in routing)

    # Prepare static classes for extensions

    # TODO: fix up naming
    for src_base, nodes in common_folders.items():
        src_folder = os.path.join(*src_base)  # "splat" list for os.path.join
        import pkg_resources
        src_path = pkg_resources.resource_filename(__name__, src_folder)
        # get structure of each folder
        contents = get_folder_contents(src_path)
        # TODO: treat per-file the same as for files below
        # TODO: could optimise so that if clobber, don't render previous
        # (unlikely to occur though)
        for filename in contents:
            out_filename = filename
            abs_filename = os.path.join(src_folder, filename)
            abs_filename = pkg_resources.resource_filename(
                __name__, abs_filename)
            with open(abs_filename) as fh:
                file_data = fh.read()

            template_renderer = None
            extension = os.path.splitext(filename)[1]
            if extension in extension_renderers:
                template_renderer = extension_renderers[extension]

                # and strip extension from output file
                out_filename = out_filename[:-len(extension)]

                import time
                version_banner = ("autonetkit_%s" %
                                  pkg_resources.get_distribution("autonetkit").version)
                date = time.strftime("%Y-%m-%d %H:%M", time.localtime())
                render_template = template_renderer.prepare(file_data)

            for node in nodes:
                # node_data = template_renderer.render(render_template,
                 # node, version_banner, date)
                if template_renderer:
                    node_data = template_renderer.render(render_template,
                                                         node, version_banner, date)
                else:
                    node_data = file_data

                # to memory -> store

                dst = folder_dsts[node][src_base]
                if isinstance(dst, basestring):
                    pass
                else:
                    dst = os.path.join(*dst)
                dst = os.path.join(dst, out_filename)
                dst = os.path.join(base_folder, dst)

                # else to file
                if to_memory:
                    node.set(dst, node_data)
                else:
                    archive.writestr(dst, node_data)

    for src, nodes in common_files.items():
        # TODO: write this to a separate function
        filename = os.path.join(*src)  # "splat" list for os.path.join
        import pkg_resources
        # TODO: specify the full file path (or provide wrapper for this to
        # specify the package)
        abs_filename = pkg_resources.resource_filename(__name__, filename)
        with open(abs_filename) as fh:
            file_data = fh.read()

        # TODO: Only do the following for .mako
        extension = os.path.splitext(filename)[1]
        template_renderer = extension_renderers[extension]

        import time
        version_banner = ("autonetkit_%s" %
                          pkg_resources.get_distribution("autonetkit").version)
        date = time.strftime("%Y-%m-%d %H:%M", time.localtime())
        render_template = template_renderer.prepare(file_data)

        # get extension

        for node in nodes:
            node_data = template_renderer.render(render_template,
                                                 node, version_banner, date)

            # to memory -> store
            dst = file_dsts[node][src]
            dst = os.path.join(base_folder, dst)

            # else to file
            if to_memory:
                node.set(dst, node_data)
            else:
                archive.writestr(dst, node_data)

    # TODO: to save memory could process for each node that has this file, etc?
    # then write that to the archive, and continue on
    # eg file by file rather than node by node?

    # TODO: if a file is greater than a certain size dont cache in memory

    # TODO: alternative would be to cache on the fly as seen, but this could s
    # another alternative is to cache if seen for second time?

# note: may want "platform render data" and a "platform renderer"


# TODO: also create a render_topology(topology)
# note that we don't have as much need to do caching as much less
# topologies than node

def render_topology(topology):
    """Pre-caches"""
    # TODO: also need to render the topology template eg lab.conf

    render_data = topology.render2
    base_folder = render_data.base_folder

    archive_filename = render_data.archive
    archive = None
    to_memory = True
    if archive_filename:
        to_memory = False
        import zipfile
        archive_filename = "%s.zip" % archive_filename
        # TODO: make rendered folder set in config, and check exists
        archive_path = os.path.join("rendered", archive_filename)
        # TODO: look at compression levels
        archive = zipfile.ZipFile(archive_path, mode='w')

    nodes = render_data.nodes
    render_nodes(nodes,
                 archive=archive,
                 base_folder=base_folder)

    if isinstance(base_folder, basestring):
        pass
    else:
        base_folder = os.path.join(*base_folder)

    for entry in render_data.get_files():
        src = entry.src
        dst = entry.dst
    # TODO: write this to a separate function
        filename = os.path.join(*src)  # "splat" list for os.path.join
        print filename
        import pkg_resources
        # TODO: specify the full file path (or provide wrapper for this to
        # specify the package)
        abs_filename = pkg_resources.resource_filename(__name__, filename)
        with open(abs_filename) as fh:
            file_data = fh.read()

        # TODO: Only do the following for .mako
        extension = os.path.splitext(filename)[1]
        template_renderer = extension_renderers[extension]

        import time
        version_banner = ("autonetkit_%s" %
                          pkg_resources.get_distribution("autonetkit").version)
        date = time.strftime("%Y-%m-%d %H:%M", time.localtime())
        render_template = template_renderer.prepare(file_data)

        # get extension
        # TODO: clean up placeholder for node renderer
        node = None
        template_data = {'topology': topology}

        topology_data = template_renderer.render(render_template,
                                                 node, date, version_banner, template_data)

        # to memory -> store
        dst = os.path.join(base_folder, dst)
        if isinstance(dst, basestring):
            pass
        else:
            dst = os.path.join(*dst)

        # else to file
        if to_memory:
            topology.set(dst, topology_data)
        else:
            archive.writestr(dst, topology_data)

    # render files

    if archive:
        archive.close()

    # warn if any folders that not supported yet for topologies


def render(nidb):
    log.info("Rendering v2")
    # TODO: should allow render to take list of nodes in case different namespace
    # perhaps allow render to take list of topologies/nodes to render?
    for topology in nidb.topologies():
        render_topology(topology)
