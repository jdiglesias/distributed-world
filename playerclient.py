
import aiohttp
from aiohttp import web
import asyncio
import sys
import argparse
import os

DEFAULT_CORE_SERVER_HOST = os.getenv('HOST', '0.0.0.0')
DEFAULT_CORE_SERVER_PORT = 8080
DEFAULT_X = 0
DEFAULT_Y = 0

known_players = {}
async def connect_to_server_client(server_host, server_port, client_id, location):
    server_url = 'http://{}:{}/playerclient/connect'.format(server_host, server_port)
    session = aiohttp.ClientSession()
    async with session.ws_connect(server_url) as ws:
        await ws.send_json({'type': 'init', 'location': location, 'id': client_id})
        server_queue = asyncio.Queue()
        asyncio.create_task(client_write(ws, server_queue))
        loop = asyncio.get_event_loop()
        loop.add_reader(sys.stdin, send_user_input, server_queue, client_id)
        # asyncio.create_task(send_user_input(server_queue, client_id))
        async for msg in ws:
            print('Message received from serverclient: ', msg)
            json = msg.json()
            # if json['type'] == 'move':
            #     if json['player'] in known_players:



async def run(core_host, core_port, location, client_id):
    core_url = 'http://{}:{}/playerclient/connect'.format(core_host, core_port)
    session = aiohttp.ClientSession()
    async with session.ws_connect(core_url) as ws:
        await ws.send_json({'type': 'init', 'location': location, 'id': client_id})
        async for msg in ws:
            json = msg.json()
            if json['type'] == 'assign_server':
                asyncio.create_task(connect_to_server_client(json['host'], json['port'], client_id, location))
            print('Message received from core server:', msg)

async def client_write(ws: web.WebSocketResponse, queue: asyncio.Queue):
    while not ws.closed:
        json = await queue.get()
        await ws.send_json(json)

def send_user_input(queue: asyncio.Queue, client_id):
    input = sys.stdin.readline().strip()
    if input in ['up', 'down', 'left', 'right']:
        msg = {'type': 'move', 'direction': input, 'id': client_id}
    asyncio.create_task(queue.put(msg))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Initiate a connection between a server client and the core server.')
    parser.add_argument('--position-x', default=DEFAULT_X, type=str,
                        help='the host to connect to on the server client')
    parser.add_argument('--position-y', default=DEFAULT_Y, type=str,
                        help='the port to connect to on the server client')
    parser.add_argument('--core-server-host', default=DEFAULT_CORE_SERVER_HOST, type=str,
                        help='the host to connect to on the coreserver')
    parser.add_argument('--core-server-port', default=DEFAULT_CORE_SERVER_PORT, type=str,
                        help='the host to connect to on the coreserver')
    parser.add_argument('client_id', type=str,
                        help='the id of the client')
    args = vars(parser.parse_args())
    core_server_host = args['core_server_host']
    core_server_port = args['core_server_port']
    position_x = args['position_x']
    position_y = args['position_y']
    client_id = args['client_id']

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(core_server_host, core_server_port, (position_x, position_y), client_id))
