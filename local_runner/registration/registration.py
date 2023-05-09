import asyncio
import random
import string
import websockets
from local_runner import creds
import json


class RegistrationHandler:
    def __init__(self, url: str, rotation_duration: float):
        self.url = url
        self.rotation_duration = rotation_duration

    async def run(self) -> creds.Creds:
        async def handle_connection(conn: websockets.WebSocketClientProtocol) -> creds.Creds:
            challenge = generate_challenge(8, 4)
            print("Code", challenge)
            await conn.send(json.dumps({
                "__action__": "register",
                "challenge": challenge,
            }))
            while True:
                response = await conn.recv()

                data = json.loads(response)
                action = data.get("__action__")

                if action == "client_credentials":
                    client_id = data.get("__client_id__")
                    client_secret = data.get("__client_secret__")
                    if client_id and client_secret:
                        return creds.Creds(client_id=client_id, client_secret=client_secret)
                    else:
                        raise ValueError("Missing client_id or client_secret in the response")
                elif action == "registration_success":
                    print("ready to pair")
                else:
                    print("Unknown action", action)

        while True:
            try:
                async with websockets.connect(self.url) as websocket:
                    print("Connected to websocket")
                    while True:
                        try:
                            c = await asyncio.wait_for(handle_connection(websocket), timeout=self.rotation_duration)
                            break
                        except asyncio.TimeoutError:
                            continue
                    print("Paired successfully")
                    return c
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(5)


def generate_challenge(chars: int, group_len: int) -> str:
    allowed_chars = string.ascii_uppercase + string.digits
    result = []
    for i in range(chars):
        result.append(random.choice(allowed_chars))
        if (i + 1) % group_len == 0 and i != chars - 1:
            result.append('-')
    return ''.join(result)


async def register(url: str, rotation_duration: float) -> creds.Creds:
    return await RegistrationHandler(url, rotation_duration).run()
