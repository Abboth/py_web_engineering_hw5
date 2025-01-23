import asyncio
import aiohttp
import logging
import websockets
import names

from prettytable import PrettyTable
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK


class ChatServer:
    clients = set()

    async def register_client(self, websocket: WebSocketServerProtocol):
        websocket.name = names.get_full_name()
        self.clients.add(websocket)
        logging.info(f"new client {websocket.remote_address} connects")

    async def unregister_client(self, websocket: WebSocketServerProtocol):
        self.clients.remove(websocket)
        logging.info(f"client {websocket.remote_address} disconnects")

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def ws_handler(self, websocket: WebSocketServerProtocol):
        await self.register_client(websocket)
        try:
            await self.distribute_message(websocket)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister_client(websocket)

    async def distribute_message(self, websocket: WebSocketServerProtocol):
        async for message in websocket:
            if message == "exchange":
                exchange_data = await get_exchange()
                await self.send_to_clients(str(exchange_data))
            else:
                await self.send_to_clients(f"{websocket.name}: {message}")


async def request(url: str):
    async with aiohttp.ClientSession() as client:
        r = await client.get(url)
        if r.status == 200:
            result = r.json()
            return result
        else:
            return "can't to get data, server not responding"


async def get_exchange():
    response = await request(f'https://api.privatbank.ua/p24api/pubinfo?exchange&coursid=5')
    data = await parse_data(response)
    result = await pretty_view(data)

    return result


async def pretty_view(data):
    table = "Currency    Sale Rate    Purchase Rate\n"
    table += "----------  ----------  --------------\n"

    for item in data:
        table += f"{item['ccy']:10}  {item['sale']:10}  {item['buy']:14}\n"
    return table


async def parse_data(data):
    parsed_data = []
    for currency in await data:
        if currency["ccy"] in ["USD", "EUR"]:
            parsed_data.append(currency)
    return parsed_data


async def main():
    server = ChatServer()
    async with websockets.serve(server.ws_handler, 'localhost', 8080):
        await asyncio.Future()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
