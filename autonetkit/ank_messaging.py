#!/usr/bin/python
# -*- coding: utf-8 -*-
import autonetkit.ank_json
import autonetkit.config as config
import autonetkit.log as log
from autonetkit.ank_utils import call_log

use_http_post = config.settings['Http Post']['active']
if use_http_post:
    import urllib

#@call_log


def format_http_url(host=None, port=None, route='publish'):
    if not host and not port:
        host = config.settings['Http Post']['server']
        port = config.settings['Http Post']['port']
    return 'http://%s:%s/%s' % (host, port, route)


default_http_url = format_http_url()

#@call_log


def update_vis(anm=None, nidb=None, http_url=None, uuid=None):
    if http_url is None:
        http_url = default_http_url

    if anm and nidb:
        body = autonetkit.ank_json.dumps(anm, nidb)
    elif anm:
        body = autonetkit.ank_json.dumps(anm)
    else:
        import json
        body = json.dumps({})  # blank to test visualisation server running

    if uuid is None:
        uuid = get_uuid(anm)

    params = urllib.urlencode({'body': body, 'type': 'anm',
                               'uuid': uuid})
    try:
        data = urllib.urlopen(http_url, params).read()
        log.debug(data)
    except IOError, e:
        log.info('Unable to connect to visualisation server %s', http_url)
        return

    if not anm:

        # testing

        log.info('Visualisation server running')

#@call_log


def get_uuid(anm):
    try:
        return config.settings['Http Post']['uuid']
    except KeyError:
        log.warning('UUID not set, returning singleuser uuid')
        return 'singleuser'


#@call_log
def highlight(nodes=None, edges=None, paths=None, path=None,
              uuid='singleuser', http_url=None):
    if http_url is None:
        http_url = default_http_url
    if not paths:
        paths = []

    if path:
        paths.append(path)

    if nodes is None:
        nodes = []
    if edges is None:
        edges = []

    def nfilter(n):
        try:
            return n.id
        except AttributeError:
            return n  # likely already a node id (string)

    def efilter(e):
        try:
            return (e.src.id, e.dst.id)
        except AttributeError:
            return e  # likely already edge (src, dst) id tuple (string)

    nodes = [nfilter(n) for n in nodes]
    # TODO: allow node annotations also

    filtered_edges = []
    for edge in edges:
        if isinstance(edge, dict) and 'edge' in edge:
            edge_data = dict(edge)  # use as-is (but make copy)
        else:
            edge_data = {'edge': edge}  # no extra data

        edge_data['src'] = edge_data['edge'].src.id
        edge_data['dst'] = edge_data['edge'].dst.id
        del edge_data['edge']  # remove now have extracted the src/dst
        filtered_edges.append(edge_data)

    #edges = [efilter(e) for e in edges]
    filtered_paths = []
    for path in paths:

        # TODO: tidy this logic

        if isinstance(path, dict) and 'path' in path:
            path_data = dict(path)  # use as-is (but make copy)
        else:
            # path_data = {'path': path, 'verified': is_verified}

            path_data = {'path': path}

        path_data['path'] = [nfilter(n) for n in path_data['path']]
        filtered_paths.append(path_data)

    # TODO: remove "highlight" from json, use as url params to distinguish

    import json
    body = json.dumps({'nodes': nodes, 'edges': filtered_edges,
                       'paths': filtered_paths})

    params = urllib.urlencode({'body': body, 'type': 'highlight',
                               'uuid': uuid})

    # TODO: split this common function out, create at runtime so don't need to
    # keep reading config

    try:
        urllib.urlopen(http_url, params).read()
    except IOError, error:
        log.info('Unable to connect to HTTP Server %s: %s', http_url, error)
