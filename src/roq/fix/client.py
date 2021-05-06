""" FIX Tools
"""

import asyncio

from datetime import datetime, timedelta

import simplefix


_READ_BUFFER_SIZE = 4096


class Client:
    """Client connection"""

    def __init__(self, fix_version, sender_comp_id, target_comp_id, heart_bt_int):
        """constructor"""
        self.reader = self.writer = self.timer = None
        self.fix_version = fix_version
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.heart_bt_int = heart_bt_int
        self.next_send_seq_num = 1
        self.next_recv_seq_num = 1
        self.ready = False
        self.closing = False
        self.request_sent = None
        self.next_test_request = None
        self.remote_heartbeat_timeout = None
        self.remote_heart_bt_int = None
        self.remote_test_request_timeout = None

    @classmethod
    async def create(
        cls,
        hostname,
        port,
        fix_version,
        sender_comp_id,
        target_comp_id,
        heart_bt_int,
    ):
        """factory method to create an instance"""
        self = Client(fix_version, sender_comp_id, target_comp_id, heart_bt_int)
        self.reader, self.writer = await asyncio.open_connection(hostname, port)
        loop = asyncio.get_event_loop()
        self.timer = loop.create_task(self._timer())
        return self

    async def on_logon(self):
        """logon event handler"""

    async def on_logout(self):
        """logout event handler"""

    async def dispatch(self):
        """read from stream and dispatch messages"""
        await self.send_logon(heart_bt_int=30)
        self.request_sent = datetime.now()
        parser = simplefix.FixParser()
        done = False
        while not done:
            data = await self.reader.read(_READ_BUFFER_SIZE)
            if len(data) == 0:
                print("WARN: EOF")
                break
            parser.append_buffer(data)
            while not done:
                message = parser.get_message()
                if message is None:
                    break
                print(f"Message: {message}")
                if message.message_type == simplefix.MSGTYPE_LOGON:
                    done = await self._on_logon(message)
                elif message.message_type == simplefix.MSGTYPE_LOGOUT:
                    done = await self._on_logout(message)
                elif message.message_type == simplefix.MSGTYPE_TEST_REQUEST:
                    done = await self._on_test_request(message)
                elif message.message_type == simplefix.MSGTYPE_HEARTBEAT:
                    done = await self._on_heartbeat(message)
                else:
                    print("WARN: Unhandled message")
        await self._close()
        print("Close the connection")
        self.writer.close()
        await self.writer.wait_closed()

    async def send_logon(self, heart_bt_int):
        """send a logon message"""
        await self._send(
            {
                simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_LOGON,
                simplefix.TAG_HEARTBTINT: heart_bt_int,
            }
        )

    async def send_logout(self, text):
        """send a logout message"""
        await self._send(
            {
                simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_LOGOUT,
                simplefix.TAG_TEXT: text,
            }
        )

    async def send_test_request(self, test_req_id):
        """send a logout message"""
        now = datetime.now()
        await self._send(
            {
                simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_TEST_REQUEST,
                simplefix.TAG_TESTREQID: test_req_id,
            }
        )
        self.next_test_request = now + timedelta(seconds=self.heart_bt_int)
        if self.remote_heartbeat_timeout is not None:
            print("WARN: Missed a heartbeat")
        self.remote_heartbeat_timeout = now + timedelta(seconds=10)

    async def send_heartbeat(self, test_req_id):
        """send a logout message"""
        await self._send(
            {
                simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_HEARTBEAT,
                simplefix.TAG_TESTREQID: test_req_id,
            }
        )

    async def _send(self, params):
        """helper method to encode a message and write to stream"""
        message = simplefix.FixMessage()
        # standard header
        message.append_pair(simplefix.TAG_BEGINSTRING, f"FIX.{self.fix_version}")
        message.append_pair(simplefix.TAG_SENDER_COMPID, self.sender_comp_id)
        message.append_pair(simplefix.TAG_TARGET_COMPID, self.target_comp_id)
        message.append_pair(simplefix.TAG_MSGSEQNUM, self.next_send_seq_num)
        if not message.get(simplefix.TAG_SENDING_TIME):
            message.append_utc_timestamp(simplefix.TAG_SENDING_TIME)
        # body
        for key, value in params.items():
            if isinstance(value, datetime):
                header = key == simplefix.TAG_SENDING_TIME
                message.append_utc_timestamp(key, value, header=header)
            else:
                message.append_pair(key, value)
        self.next_send_seq_num += 1
        # encode
        buffer = message.encode()
        # send
        print(f"Sending: {buffer}")
        self.writer.write(buffer)
        await self.writer.drain()

    async def _on_logon(self, message):
        if self.ready or self.closing:
            raise RuntimeError("Unexpected Logon")
        # note! default to zero
        heart_bt_int = message.get(simplefix.TAG_HEARTBTINT)
        self.remote_heart_bt_int = 0 if heart_bt_int is None else int(heart_bt_int)
        self._update_remote_test_request_timeout()
        self.ready = True
        self.request_sent = None
        await self.on_logon()
        now = datetime.now()
        await self.send_test_request(f"{now}")
        return False

    async def _on_logout(self, message):
        res = False
        if self.closing:
            res = True
            self.request_sent = None
        else:
            await self.send_logout(text="bye")
            self.ready = False
            self.closing = True
            self.request_sent = datetime.now()
        await self.on_logout()
        return res

    async def _on_test_request(self, message):
        self._update_remote_test_request_timeout()
        test_req_id = message.get(simplefix.TAG_TESTREQID)
        await self.send_heartbeat(test_req_id=test_req_id)
        return False

    def _update_remote_test_request_timeout(self):
        if self.remote_heart_bt_int > 0:
            now = datetime.now()
            timeout = timedelta(seconds=int((self.remote_heart_bt_int * 5) / 4))
            self.remote_test_request_timeout = now + timeout

    async def _on_heartbeat(self, message):
        self.remote_heartbeat_timeout = None
        return False

    async def _timer(self):
        try:
            while True:
                if self.ready:
                    await self._check_our_heartbeat()
                    await self._check_remote_heartbeat()
                else:
                    await self._check_our_request()
                await asyncio.sleep(1)
        except RuntimeError as err:
            print(f"ERROR: {err}")
            loop = asyncio.get_event_loop()
            loop.stop()

    async def _check_our_request(self):
        now = datetime.now()
        if self.request_sent is not None:
            timeout = (now - self.request_sent) > timedelta(seconds=10)
            if timeout:
                if self.closing:
                    print("WARN: Logout request has timed out, stream will be closed now")
                    await self._close()
                else:
                    raise RuntimeError("Logon request has timed out")

    async def _check_our_heartbeat(self):
        now = datetime.now()
        # remote heartbeat
        if self.remote_heartbeat_timeout is not None and now > self.remote_heartbeat_timeout:
            raise RuntimeError("Heartbeat has not been received")
        # our request for heartbeat
        if self.next_test_request is not None and now > self.next_test_request:
            await self.send_test_request(f"{now}")

    async def _check_remote_heartbeat(self):
        now = datetime.now()
        # remote request for heartbeat
        if self.remote_heart_bt_int is not None and now > self.remote_test_request_timeout:
            raise RuntimeError("Remote request for heartbeat has not been received")

    async def _close(self):
        print("Closing the stream")
        self.writer.close()
        await self.writer.wait_closed()
