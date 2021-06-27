import logging

import aiohttp
import aiohttp_jinja2
import jinja2
import pkg_resources
from aiohttp import web

logger = logging.getLogger(__name__)


def main():
    """

    @return:
    """

    async def websocket_handler(request):
        """

        @param request:
        @return:
        """
        ws = web.WebSocketResponse()
        request.app.websockets.add(ws)
        await ws.prepare(request)
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    if msg.data == 'close':
                        await ws.close()
                        request.app.websockets.remove(ws)
                    else:
                        await ws.send_str("Connected")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.warning('ws connection closed with exception %s' %
                                   ws.exception())

        finally:
            request.app.websockets.remove(ws)
        return ws

    @aiohttp_jinja2.template('index.jinja2')
    async def index(request):
        """

        @param request:
        @return:
        """
        if request.app.data is None:
            return web.Response(text="No topology set")

        topology_name = request.query.get("topology")
        topology_names = list(request.app.data.keys())

        try:
            topology = request.app.data[topology_name]
        except KeyError:
            topology = request.app.data["physical"]

        return {'topology': topology, 'topology_names': topology_names, "topology_name": topology_name}

    async def hello(request):
        """

        @param request:
        @return:
        """
        return web.json_response(request.app.data)

    async def post_handler(request):
        """

        @param request:
        @return:
        """
        data = await request.json()
        request.app.data = data
        for ws in request.app.websockets:
            await ws.send_str("Updated")

        return web.Response(text="Data stored")

    app = web.Application()
    app.data = None
    app.websockets = set()
    app.add_routes([web.get('/', index)])
    app.add_routes([web.get('/data', hello)])
    app.add_routes([web.post('/data', post_handler)])
    app.add_routes([web.get('/ws', websocket_handler)])

    resource_package = __name__
    path_to_template_folder = pkg_resources.resource_filename(resource_package, 'templates')
    path_to_static_folder = pkg_resources.resource_filename(resource_package, 'static')


    aiohttp_jinja2.setup(app,
                         loader=jinja2.FileSystemLoader(path_to_template_folder))



    app.add_routes([web.static('/static', path_to_static_folder)])

    web.run_app(app)


if __name__ == '__main__':
    main()
