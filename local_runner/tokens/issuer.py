import base64
import json
import requests
import threading
from datetime import datetime, timedelta
from local_runner.creds import Creds


class Issuer:
    def __init__(self, creds: Creds):
        self.creds = creds
        self.token = ""
        self.token_expires = datetime.min
        self.http_client = requests.Session()
        self.auth_url = "https://authorization-tokens.global.ctrlstack.com/token"
        self.max_refresh_interval = timedelta(hours=1)
        self.mx = threading.Lock()

    def get_token(self) -> str:
        now = datetime.utcnow()
        if self.token_expires < now:
            with self.mx:
                if self.token_expires < now:
                    token = self._get_auth_token()

                    # Parse token and make sure we don't keep expiring ones for too long
                    parts = token.split(".")
                    if len(parts) != 3:
                        raise ValueError(f"JWT should be 3 dot-delimited parts, found {len(parts)}")

                    claim_str = parts[1]
                    while len(claim_str) % 4:
                        claim_str += "="

                    claim_bytes = base64.urlsafe_b64decode(claim_str)
                    claims = json.loads(claim_bytes)

                    expires = datetime.utcfromtimestamp(claims["exp"])
                    if expires > now + self.max_refresh_interval:
                        expires = now + self.max_refresh_interval

                    self.token = token
                    self.token_expires = expires

        return self.token

    def _get_auth_token(self) -> str:
        payload = {
            "clientId": self.creds.client_id,
            "clientSecret": self.creds.client_secret
        }
        headers = {"Content-Type": "application/json"}

        response = self.http_client.post(self.auth_url, json=payload, headers=headers)
        response.raise_for_status()
        jwt = response.json().get("JWT")
        if not jwt:
            raise ValueError("Error unmarshaling response body for {}: JWT not found".format(self.auth_url))

        return jwt

    def invalidate(self):
        with self.mx:
            self.token = ""
            self.token_expires = datetime.min
