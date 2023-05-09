import json
import os
from dataclasses import dataclass
from typing import Optional
from local_runner.config import ENV_PREFIX


@dataclass
class Creds:
    client_id: str
    client_secret: str

    def to_dict(self):
        return {
            "clientId": self.client_id,
            "clientSecret": self.client_secret
        }


class NotFoundError(Exception):
    pass


ENV_CLIENT_ID = f"{ENV_PREFIX}_CLIENT_ID"
ENV_CLIENT_SECRET = f"{ENV_PREFIX}_CLIENT_SECRET"


def default(location: str) -> Creds:
    try:
        return from_file(location)
    except FileNotFoundError:
        pass

    creds = from_env()
    if creds is not None:
        return creds

    raise NotFoundError("credentials not found")


def from_file(location: str) -> Creds:
    location = os.path.expanduser(location)
    with open(location) as f:
        creds = json.load(f)

    return Creds(client_id=creds["clientId"], client_secret=creds["clientSecret"])


def from_env() -> Optional[Creds]:
    client_id = os.getenv(ENV_CLIENT_ID)
    client_secret = os.getenv(ENV_CLIENT_SECRET)

    if client_id and client_secret:
        return Creds(client_id=client_id, client_secret=client_secret)
    else:
        return None


def store(location: str, creds: Creds) -> None:
    location = os.path.expanduser(location)
    os.makedirs(os.path.dirname(location), mode=0o700, exist_ok=True)

    with open(location, "w") as f:
        json.dump(creds.to_dict(), f, indent=2)
