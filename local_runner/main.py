import asyncio
import sys
import argparse

import requests

from local_runner.comms import Listener, HttpReporter
from local_runner import config
from local_runner.tokens import Issuer
from local_runner import creds
from local_runner import exec
from local_runner.registration import register
from local_runner import handler


async def _main(args):
    cfg = config.default()
    try:
        c = creds.default(cfg.credentials_file)
    except creds.NotFoundError:
        print("Credentials not found. Initiating pairing...")
        try:
            c = await asyncio.wait_for(register(cfg.registration_url, cfg.registration_code_rotation), cfg.registration_timeout)
        except asyncio.TimeoutError:
            print("Pairing timed out")
            sys.exit(1)
        creds.store(cfg.credentials_file, c)

    issuer = Issuer(c)
    issuer.auth_url = cfg.auth_url
    mgr = exec.Manager(2)
    mgr.start()

    session = requests.Session()
    reporter = HttpReporter(session)
    h = handler.Handler(mgr, reporter, cfg)
    listener = Listener(h.handle, args.role_level)
    print("[ctrl+c] to exit")
    if args.role_level:
        print("\033[3mrole-level runner enabled, will process all requests for the registered role\033[0m")
    try:
        await listener.listen(cfg.ws_url, issuer.get_token)
    except asyncio.CancelledError:
        print("shutting down...")
    await mgr.stop(10.0)


def entry_point(args):
    try:
        asyncio.run(_main(args))
    except KeyboardInterrupt:
        print("bye")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role-level", action="store_true", help="register as role-level runner")
    args = parser.parse_args()
    entry_point(args)
