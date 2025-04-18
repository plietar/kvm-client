import asyncio
import struct
from dataclasses import dataclass
from contextlib import AsyncExitStack
from typing import Protocol, Any, Self

from . import asp2000
from .proto import IUSB, KVMHeader, KVMPayload


def encode_keys(keys: list[int]) -> bytes:
    assert len(keys) < 6
    return struct.pack("<BBBBBBBB", 0, 0, *keys, *([0] * (6 - len(keys))))


@dataclass
class ConnectionParameters:
    hostname: str
    port: int
    token: bytes


class Connection:
    def __init__(self, hostname: str, port: int):
        self.hostname = hostname
        self.port = port
        self.stack = AsyncExitStack()

    async def __aenter__(self) -> Self:
        self.reader, self.writer = await asyncio.open_connection(
            self.hostname, self.port
        )
        # TODO:
        # self.stack.push_async_callback(lambda: self.writer.close)
        # self.stack.push_async_callback(self.writer.wait_closed)
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> Any:
        return await self.stack.__aexit__(exc_type, exc_value, traceback)

    async def recv(self) -> tuple[Any, Any]:
        header = KVMHeader.parse(await self.reader.readexactly(7))
        payload = KVMPayload.parse(
            await self.reader.readexactly(header.length), op=header.op
        )
        return header, payload

    async def send(self, opcode: int, payload: bytes) -> None:
        header = KVMHeader.build(
            {
                "op": opcode,
                "length": len(payload),
                "status": 0,
            }
        )
        self.writer.write(header + payload)
        await self.writer.drain()


class KVMOutput(Protocol):
    def update_size(self, width: int, height: int) -> None: ...
    def update_rect(self, x: int, y: int, data: list[asp2000.YUV]) -> None: ...


class KVM:
    def __init__(self, params: ConnectionParameters, output: KVMOutput) -> None:
        self._hostname = params.hostname
        self._port = params.port
        self._token = params.token
        self._output = output
        self._decoder = asp2000.Decoder()
        self._seqno = 0

    async def __aenter__(self) -> Self:
        try:
            async with AsyncExitStack() as stack:
                self._connection = await stack.enter_async_context(
                    Connection(self._hostname, self._port)
                )
                await self._connection.send(0x22, self._token)
                (header, payload) = await self._connection.recv()
                if header.op != 0x23:
                    raise ValueError("Invalid packet received")
                if payload != b"\x01":
                    raise ValueError("KVM authentication failed")
                self._stack = stack.pop_all()
        except BaseException as e:
            print(e)
            raise

        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> Any:
        return await self._stack.__aexit__(exc_type, exc_value, traceback)

    async def poll(self) -> None:
        header, data = await self._connection.recv()
        if header.op == 0x05:
            self._output.update_size(
                data.payload.data.SourceMode_X, data.payload.data.SourceMode_Y
            )

            for update in self._decoder.decode(
                data.payload.data.SourceMode_X,
                data.payload.data.SourceMode_Y,
                data.payload.data.data,
            ):
                self._output.update_rect(*update)

    async def loop(self) -> None:
        while True:
            await self.poll()

    async def send_keys(self, keys: list[int]) -> None:
        report = encode_keys(keys)
        report = struct.pack("<B", len(report)) + report
        payload = IUSB.build(
            {
                "header_length": 32,
                "header_checksum": 0,
                "dataPacketLen": len(report),
                "serverCaps": 0,
                "deviceType": 48,
                "protocol": 16,
                "direction": 128,
                "deviceNumber": 2,
                "interfaceNumber": 0,
                "clientData": b"\0\0",
                "sequenceNumber": self._seqno,
                "reserved": b"\0\0\0\0",
            }
        )
        payload += report
        await self._connection.send(0x06, payload)
        self._seqno += 1
