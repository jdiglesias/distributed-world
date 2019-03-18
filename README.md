# Distributed World

A distributed online world building game

## Installation

clone the repo, cd into it, optionally create a virtualenv, then install the required packages:
```
pip install -r requirements.txt
```

## Running

first run the core server, uses host 0.0.0.0 and port 8080 by default.
```
python coreserver.py
```
you can pass in a port and a host with `--port {port number}` and `--host {host name}`

then run a server client, listens on 8081 by default, but host and port can be provided as with previous
```
python serverclient.py
```

initialize the server client to connect to the core server by running init, giving the server client an id to register with the core server
```
python init.py "my-server-client"
```

you can point this command at the previously started core server and server client (but it uses their defaults here as well) by using the following, 
`--server-client-port {port number}` `--server-client-host {host name}`  `--core-server-port {port number}` `--core-server-host {host name}`

finally, start a player client, with a client id
```
python playerclient.py "my-player-client"
```

you can pass in `--position-x` and `--position-y` to give a position on the map to start at, and  
`--core-server-port {port number}` `--core-server-host {host name}` to point at the core server

Now, from the player client, type commands. Currently there are `left`, `right`, `up` and `down` to move around the map. Try adding more server clients (up to 4) and player clients

