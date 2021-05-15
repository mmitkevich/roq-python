#!/usr/bin/env python

""" Test FIX Bridge
"""

import argparse
import asyncio
import logging

from urllib.parse import urlparse

import simplefix

from roq.fix import Client


class BasicTest:
    """Some test"""

    def __init__(self, client):
        """constructor"""
        self.client = client
        # don't know a better way to do this
        self.client.on_logon = self.on_logon
        self.client.on_logout = self.on_logout
        self.client.on_message = self.on_message

    async def dispatch(self):
        """dispatch"""
        await self.client.dispatch()

    async def on_logon(self):
        """logon event handler"""
        logging.info("LOGON")
        # await self.client.send(
        #     {
        #         simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_MARKET_DATA_REQUEST,
        #         267: 2,  # NO_MD_ENTRY_TYPES
        #         269: 0,  # MD_ENTRY_TYPE = BID
        #         269: 1,  # MD_ENTRY_TYPE = OFFER
        #         146: 1,  # NO_RELATED_SYM
        #         simplefix.TAG_SYMBOL: "BTC-PERPETUAL-INDEX",
        #         207: "deribit",  # SECURITY_EXCHANGE
        #     }
        #)

    async def on_logout(self):
        """logout event handler"""
        logging.info("LOGOUT")

    async def on_message(self, message):
        """generic message event handler"""
        logging.info("MESSAGE: %s", message)


async def run(uri, fix_version, sender_comp_id, target_comp_id, heart_bt_int):
    """foo"""
    uri = urlparse(uri)
    print(uri)
    if uri.scheme != "tcp":
        raise RuntimeError(f"Expected scheme 'tcp', got '{uri.scheme}'")
    [hostname, port] = uri.netloc.split(":")
    client = await Client.create(
        hostname,
        port,
        fix_version,
        sender_comp_id,
        target_comp_id,
        heart_bt_int,
    )
    await BasicTest(client).dispatch()


def main():
    """entry point"""

    parser = argparse.ArgumentParser(description="roq-fix-bridge test harness")

    parser.add_argument(
        "--loglevel",
        type=str,
        default="warning",
        help="Log level",
    )
    parser.add_argument(
        "--uri",
        type=str,
        default="tcp://localhost:1234",
        help="FIX Bridge address (URI)",
    )
    parser.add_argument(
        "--fix_version",
        type=str,
        default="4.4",
        help="FIX Bridge address (URI)",
    )
    parser.add_argument(
        "--sender_comp_id",
        type=str,
        default="roq-fix-client-test",
        help="Sender component ID",
    )
    parser.add_argument(
        "--target_comp_id",
        type=str,
        default="roq-fix-bridge",
        help="Target component ID",
    )
    parser.add_argument(
        "--heart_bt_int",
        type=int,
        default=10,
        help="Heartbeat interval (seconds)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel.upper())

    asyncio.run(
        run(
            args.uri,
            args.fix_version,
            args.sender_comp_id,
            args.target_comp_id,
            args.heart_bt_int,
        )
    )


if __name__ == "__main__":
    main()
