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
        message = simplefix.FixMessage()
        message.append_pair(simplefix.TAG_MSGTYPE, simplefix.MSGTYPE_MARKET_DATA_REQUEST)
        message.append_pair(262, "REQ_ID")  # MD_REQ_ID
        message.append_pair(263, 1)  # SUBSCRIPTION_REQUEST_TYPE = SNAPSHOT + UPDATE
        message.append_pair(264, 0)  # MARKET_DEPTH = ToB
        message.append_pair(265, 1)  # MD_UPDATE_TYPE = INCREMENTAL
        message.append_pair(267, 2)  # NO_MD_ENTRY_TYPES
        message.append_pair(269, 0)  # MD_ENTRY_TYPE = BID
        message.append_pair(269, 1)  # MD_ENTRY_TYPE = OFFER
        message.append_pair(146, 1)  # NO_RELATED_SYM
        message.append_pair(simplefix.TAG_SYMBOL, "BTC-PERPETUAL")
        message.append_pair(207, "deribit")  # SECURITY_EXCHANGE
        await self.client.send(message)

    async def on_logout(self):
        """logout event handler"""
        logging.info("LOGOUT")

    async def on_message(self, message):
        """generic message event handler"""
        message_type = message.message_type.decode("utf-8")
        if message_type == "y":  # SECURITY_LIST
            await self._on_security_list(message)
        elif message_type == "d":  # SECURITY_DEFINITION
            await self._on_security_definition(message)
        elif message_type == "f":  # SECURITY_STATUS
            await self._on_security_status(message)
        elif message_type == "W":  # MARKET_DATA_SNAPSHOT_FULL_REFRESH
            await self._on_market_data_snapshot_full_refresh(message)
        elif message_type == "X":  # MARKET_DATA_INCREMENTAL_REFRESH
            await self._on_market_data_incremental_refresh(message)
        elif message_type == "Y":  # MARKET_DATA_REQUEST_REJECT
            await self._on_market_data_request_reject(message)
        else:
            logging.error("Unknown message_type='%s'", message_type)

    async def _on_security_list(self, message):
        logging.info("SECURITY_LIST: %s", message)

    async def _on_security_definition(self, message):
        logging.info("SECURITY_DEFINITION: %s", message)

    async def _on_security_status(self, message):
        logging.info("SECURITY_STATUS: %s", message)

    async def _on_market_data_snapshot_full_refresh(self, message):
        logging.info("MARKET_DATA_SNAPSHOT_FULL_REFRESH: %s", message)

    async def _on_market_data_incremental_refresh(self, message):
        logging.info("MARKET_DATA_INCREMENTAL_REFRESH: %s", message)

    async def _on_market_data_request_reject(self, message):
        logging.error("MARKET_DATA_REQUEST_REJECT: %s", message)
        pairs = self._decode_pairs(message)
        md_req_rej_reason = int(self._get_value_from_tag(pairs, 281))
        if md_req_rej_reason == 0:  # just an example -- a common enum value
            logging.error("Reason: unknown symbol")
        else:
            logging.error("Reason: <unknown>")

    @staticmethod
    def _decode_pairs(message):
        return [(int(k.decode("utf-8")), v.decode("utf-8")) for (k, v) in message.pairs]

    @staticmethod
    def _get_value_from_tag(pairs, tag):
        res = [v for (k, v) in pairs if k == 281]
        if len(res) < 1:
            raise RuntimeError(f"No tag={tag}")
        if len(res) > 1:
            raise RuntimeError(f"Multiple tag={tag}")
        return res[0]


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
