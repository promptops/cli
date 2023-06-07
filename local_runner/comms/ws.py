import json
import websockets
from typing import Callable
import logging


class Listener:
    def __init__(self, handler: Callable):
        self.handler = handler

    async def listen(self, url: str, get_token: Callable):
        while True:
            async with websockets.connect(url) as websocket:
                auth_needed = True
                while True:
                    if auth_needed:
                        token = get_token()
                        await websocket.send(json.dumps({
                            "__action__": "authorize",
                            "token": token
                        }))
                    try:
                        message = await websocket.recv()
                    except websockets.ConnectionClosed:
                        print("connection closed, reconnecting...")
                        break
                    data = json.loads(message)

                    action = data.get("__action__")
                    if action:
                        if action == "authorization_success":
                            print("Ready")
                            auth_needed = False
                        elif action in ["no_authorization", "authorization_failure"]:
                            raise ValueError(f"{action}: {data.get('__text__')}")
                        else:
                            raise ValueError(f"Unknown action: {action}")
                    else:
                        try:
                            await self.handler(data, websocket)
                        except Exception as e:
                            logging.error("error handling message", exc_info=e)
