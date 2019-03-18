import asyncio
import os
from aiohttp import web
from aiohttp.client_exceptions import ClientConnectorError

import aiohttp
import chardet
import argparse

DEFAULT_HOST = os.getenv('HOST', '0.0.0.0')
DEFAULT_PORT = 8081
player_client_queues = {}
player_locations = {}


routes = web.RouteTableDef()

def broadcast_loc(player_client):
    for player in player_client_queues.keys():
        queue = player_client_queues[player]
        msg = { 'type': 'move',
                'location': player_locations[player_client],
                'player': player_client }

        asyncio.create_task(queue.put(msg))

async def client_write(ws: web.WebSocketResponse, queue: asyncio.Queue):
    while not ws.closed:
        json = await queue.get()
        await ws.send_json(json)

def move_player(player, direction):
    print(player_locations)
    x, y = player_locations[player]
    if direction == 'up':
        y -= 1
    if direction == 'down':
        y += 1
    if direction == 'left':
        x -= 1
    if direction == 'right':
        x += 1
    player_locations[player] = (x, y)
    broadcast_loc(player)

async def init_player(ws, player_client, json):
    queue =  asyncio.Queue()
    player_client_queues[player_client] = queue
    print('setting player location')
    player_locations[player_client] = json['location']
    asyncio.create_task(client_write(ws, queue))
    broadcast_loc(player_client)

@routes.get('/playerclient/connect')
async def player_client_connect(request: web.Request):
    # TODO add UDP connection
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    async for msg in ws:
        print("Message received from player: {}".format(msg))
        json = msg.json()
        player_client = json['id']
        if json['type'] == 'init':
            asyncio.create_task(init_player(ws, player_client, json))

        if json['type'] == 'move':
            # try:
            #     queue = player_client_queues[player_client]
            # except KeyError:
            #     raise ConnectionError('Connection with {} not initialized!'.format(player_client))
            move_player(player_client, json['direction'])


        if msg.type == aiohttp.WSMsgType.TEXT:
            print(msg.data)
            if msg.data == 'close':
                await ws.close()
    return ws

@routes.post('/init')
async def init(request: web.Request):
    body = await request.json()
    core_url = 'http://{}:{}/serverclient/connect'.format(body['host'], body['port'])
    server_client_id = body['id']
    session = aiohttp.ClientSession()
    try:
        async with session.ws_connect(core_url) as ws:
            await ws.send_json({'id': server_client_id, 'type': 'init', 'port': request.app['port'], 'host': request.app['host']})
            async for msg in ws:
                print('Message received from server:', msg)
    except ClientConnectorError as e:
        raise ConnectionError("Could not connect to core server") from e

def start_server_client(host, port):
    app = web.Application()
    app.add_routes(routes)
    app['port'] = port
    app['host'] = host
    web.run_app(app, port=port, host=host)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Initiate a connection between a server client and the core server.')
    parser.add_argument('--host', default=DEFAULT_HOST, type=str,
                        help='the host to connect to on the server client')
    parser.add_argument('--port', default=DEFAULT_PORT, type=str,
                        help='the port to connect to on the server client')
    args = vars(parser.parse_args())
    start_server_client(args['host'], args['port'])
