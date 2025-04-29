import os
from server import GameServer
from time import sleep
from dotenv import load_dotenv

load_dotenv()
SERVER_ADDRESS = os.getenv("SERVER_ADDRESS") or "0.0.0.0"
SERVER_PORT = int(os.getenv("SERVER_PORT") or 8686)

server = GameServer(ip = SERVER_ADDRESS, port = SERVER_PORT)
while True:
    server.Pump()
    sleep(0.0001)
