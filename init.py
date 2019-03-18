import aiohttp
import asyncio
import os
import argparse
import serverclient
import playerclient

DEFAULT_SERVER_CLIENT_HOST = os.getenv('HOST', '0.0.0.0')
DEFAULT_SERVER_CLIENT_PORT = 8081
DEFAULT_CORE_SERVER_HOST = os.getenv('HOST', '0.0.0.0')
DEFAULT_CORE_SERVER_PORT = 8080

async def send_init(url, core_host, core_port, client_id: str):
    async with aiohttp.ClientSession() as sesh:
        datadict = {'type': 'init', 'host': core_host, 'port': core_port, 'id': client_id}
        async with sesh.post(url, json=datadict) as resp:
            if resp.status != 200:
                raise ConnectionError('You had an error connecting to "{}": {}'.format(url, resp.status))
        sesh.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Initiate a connection between a server client and the core server.')
    parser.add_argument('--server-client-host', default=DEFAULT_SERVER_CLIENT_HOST, type=str,
                        help='the host to connect to on the server client')
    parser.add_argument('--server-client-port', default=DEFAULT_SERVER_CLIENT_PORT, type=str,
                        help='the port to connect to on the server client')
    parser.add_argument('--core-server-host', default=DEFAULT_CORE_SERVER_HOST, type=str,
                        help='the host to connect to on the coreserver')
    parser.add_argument('--core-server-port', default=DEFAULT_CORE_SERVER_PORT, type=str,
                        help='the host to connect to on the coreserver')
    parser.add_argument('client_id', type=str,
                        help='the id of the client')
    args = vars(parser.parse_args())
    print(args)
    server_client_host = args['server_client_host']
    server_client_port = args['server_client_port']
    core_server_host = args['core_server_host']
    core_server_port = args['core_server_port']
    client_id = args['client_id']
    print(client_id)
    server_client_url = 'http://' + server_client_host + ':' + str(server_client_port) + '/init'

    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_init(server_client_url, core_server_host, core_server_port, client_id))
