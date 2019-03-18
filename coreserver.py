import asyncio
import aiohttp
from aiohttp import web
from typing import Tuple
import os
import argparse

########################
# Running a distributed game begins with starting the CoreServer
# Then, a ServerClient POSTS the the CoreServer including an endpoint listening for ServerClient connections, which creates a Websocket connection back to the ServerClient
# The CoreServer responds with an area to cover and the other ServerClients covering that area, if any
# The CoreServer tells the other ServerClients that the new ServerClient is taking over this area
# The other ServerClients connect to the new ServerClient and, once acknowledged, send the state of the area, with any PlayerClients
# The other ServerClients tell their PlayerClients to connect to the new ServerClient
# The PlayerClients connect to the new ServerClient, which acknowledges
# Once the new ServerClient has all the PlayerClient connections from the old one, it informs the old ServerClient
# The old ServerClient informs the CoreServer that it has relinquished control of that area.
# Once all the old ServerClients have told the CoreServer that they have relinquished control, the start is done
# PlayerClients connect to the CoreServer, which stores their location
server_client_queues = {}
player_client_queues = {}
server_client_urls = {}
routes = web.RouteTableDef()
base_quad_tree_node = None
default_boundaries = (0, 0, 200, 200)
DEFAULT_PORT = 8080
DEFAULT_HOST = os.getenv('HOST', '0.0.0.0')
class ServerQuadTreeNode():
    def __init__(self, default_server: str, boundaries: Tuple[float, float, float, float]):
        self.default_server = default_server
        self.boundaries = boundaries
        self.top_left = None
        self.top_right = None
        self.bottom_left = None
        self.bottom_right = None

    def _get_area_boundaries(self, area_str: str) -> Tuple[float, float, float, float]:
        left, top, right, bottom = self.boundaries
        horizonal_mid =  left + ((right - left) / 2)
        vertical_mid = top + ((bottom - top) / 2)
        if area_str == 'top_left':
            return (left, top, horizonal_mid, vertical_mid)
        if area_str == 'top_right':
            return (horizonal_mid, top, right, vertical_mid)
        if area_str == 'bottom_left':
            return (left, vertical_mid, horizonal_mid, bottom)
        if area_str == 'bottom_right':
            return (horizonal_mid, vertical_mid, right, bottom)

    def assign_area(self, server: str, area: str) -> Tuple[float, float, float, float]:
        setattr(self, area, server)
        return self._get_area_boundaries(area)

    def assign_next_area(self, server: str) -> Tuple[float, float, float, float]:
        for area_str in ['top_left',
                  'top_right',
                  'bottom_left',
                  'bottom_right']:
            a = getattr(self, area_str)
            if not a:
                return self.assign_area(server, area_str)

        raise ValueError("Can't assign any more!")

    def get_location_server(self, location: Tuple[float, float]) -> str:
        left, top, right, bottom = self.boundaries
        horizonal_mid =  left + ((right - left) / 2)
        vertical_mid = top + ((bottom - top) / 2)

        xloc, yloc = location
        h = 'right' if xloc >= horizonal_mid else 'left'
        v = 'bottom' if yloc >= vertical_mid else 'top'
        area_str =  v + '_' + h
        area = getattr(self, area_str)
        print(area_str + ': {}'.format(area))
        if area:
            return area
        else:
            return self.default_server

async def assign_server_client(server_client: str):
    global base_quad_tree_node
    global default_boundaries
    queue = server_client_queues[server_client]
    if not base_quad_tree_node:
        base_quad_tree_node = ServerQuadTreeNode(server_client, default_boundaries)
        boundaries = default_boundaries
    else:
        boundaries = base_quad_tree_node.assign_next_area(server_client)

    msg = {'type': 'assign_area', 'boundaries': boundaries}
    await queue.put(msg)

async def server_client_init(ws: web.WebSocketResponse, json: dict):
    global server_client_queues
    global server_client_urls
    server_client = json['id']
    queue = asyncio.Queue()
    server_client_queues[server_client] = queue
    server_client_urls[server_client] = {'host': json['host'], 'port': json['port']}
    asyncio.create_task(client_write(ws, queue))
    await assign_server_client(server_client)


@routes.get('/serverclient/connect')
async def server_client_connect(request: web.Request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    async for msg in ws:
        print(msg)
        json = msg.json()
        if json['type'] == 'init':
            await server_client_init(ws, json)

        if msg.type == aiohttp.WSMsgType.TEXT:
            print(msg.data)
            if msg.data == 'close':
                await ws.close()
    return ws

async def player_client_init(ws: web.WebSocketResponse, player_client: str, location: Tuple[float, float]):
    global player_client_queues
    queue = asyncio.Queue()
    player_client_queues[player_client] = queue
    asyncio.create_task(client_write(ws, queue))
    await assign_player_client(player_client, location)


async def assign_player_client(player_client: str, location: Tuple[float, float]):
    global base_quad_tree_node
    global player_client_queues
    global server_client_urls
    server_id = base_quad_tree_node.get_location_server(location)
    url = server_client_urls[server_id]
    queue = player_client_queues[player_client]
    await queue.put({'host': url['host'], 'port': url['port'], 'type': 'assign_server'})


@routes.get('/playerclient/connect')
async def player_client_connect(request: web.Request):
    print('connecting to pc')
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    async for msg in ws:
        print(msg)
        json = msg.json()
        player_client = json['id']
        if json['type'] == 'init':
            location = json['location']
            await player_client_init(ws, player_client, location)

        if msg.type == aiohttp.WSMsgType.TEXT:
            print(msg.data)
            if msg.data == 'close':
                await ws.close()
    return ws

async def client_write(ws: web.WebSocketResponse, queue: asyncio.Queue):
    while not ws.closed:
        json = await queue.get()
        print('sending json to ws {}, {}'.format(ws, json))
        await ws.send_json(json)

def start_core_server(host, port):
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Initiate a connection between a server client and the core server.')
    parser.add_argument('--host', default=DEFAULT_HOST, type=str,
                        help='the host to connect to on the server client')
    parser.add_argument('--port', default=DEFAULT_PORT, type=str,
                        help='the port to connect to on the server client')
    args = vars(parser.parse_args())
    start_core_server(args['host'], args['port'])