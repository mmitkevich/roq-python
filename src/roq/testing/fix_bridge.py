#!/usr/bin/env python

""" Test FIX Bridge
"""

import argparse
import asyncio

from urllib.parse import urlparse

from roq.fix import Client


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
    await client.dispatch()


def main():
    """entry point"""

    parser = argparse.ArgumentParser(description="roq-fix-bridge test harness")

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
