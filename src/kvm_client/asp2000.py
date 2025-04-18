import struct
from typing import Iterable

YUV = tuple[int, int, int]


class BitStream:
    def __init__(self, data: bytes):
        self._data = data
        self._next = None
        self._readbuf = 0
        self._bits = 0
        self._index = 0

    def peek(self, n: int) -> int:
        assert n <= 32
        if n > self._bits:
            result = self._readbuf >> (32 - n)
            n -= self._bits
            (readbuf,) = struct.unpack_from("<L", self._data, self._index)
        else:
            result = 0
            readbuf = self._readbuf

        result |= readbuf >> (32 - n)
        return result

    def read(self, n: int) -> int:
        assert n <= 32
        if n > self._bits:
            result = self._readbuf >> (32 - n)
            n -= self._bits

            (self._readbuf,) = struct.unpack_from("<L", self._data, self._index)
            self._index += 4
            self._bits = 32
        else:
            result = 0

        self._bits -= n
        result |= self._readbuf >> (32 - n)
        self._readbuf = (self._readbuf << n) & 0xFFFFFFFF
        return result


class Decoder:
    def read_coordinates(self, bs: BitStream) -> tuple[int, int]:
        txb = bs.read(8)
        tyb = bs.read(8)
        return (txb, tyb)

    def read_palette(self, bs: BitStream, colours: list[YUV], n: int) -> list[YUV]:
        palette = []
        for i in range(n):
            newColor = bs.read(1)
            index = bs.read(2)
            if newColor:
                y = bs.read(8)
                u = bs.read(8)
                v = bs.read(8)

                # TODO: convert to RGB?
                colours[index] = (y, u, v)

            palette.append(colours[index])
        return palette

    def read_tile(self, bs: BitStream, palette: list[YUV], *, bits: int) -> list[YUV]:
        if bits == 0:
            return [palette[0]] * 64
        else:
            return [palette[bs.read(bits)] for i in range(64)]

    def next_tile(self, txb: int, tyb: int, width: int, height: int) -> tuple[int, int]:
        txb += 1
        if txb >= width // 8:
            txb = 0
            tyb += 1
            if tyb >= height // 8:
                tyb = 0
        return (txb, tyb)

    def decode(
        self, width: int, height: int, data: bytes
    ) -> Iterable[tuple[int, int, list[YUV]]]:
        colours = [
            (0x00, 0x80, 0x80),
            (0xFF, 0x80, 0x80),
            (0x80, 0x80, 0x80),
            (0xC0, 0x80, 0x80),
        ]
        txb = 0
        tyb = 0

        bs = BitStream(data)
        while True:
            code = bs.read(4)
            if code == 9:
                break
            elif code == 5:
                palette = self.read_palette(bs, colours, 1)
                yield txb, tyb, self.read_tile(bs, palette, bits=0)
                (txb, tyb) = self.next_tile(txb, tyb, width, height)
            elif code == 6:
                palette = self.read_palette(bs, colours, 2)
                yield txb, tyb, self.read_tile(bs, palette, bits=1)
                (txb, tyb) = self.next_tile(txb, tyb, width, height)
            elif code == 7:
                palette = self.read_palette(bs, colours, 4)
                yield txb, tyb, self.read_tile(bs, palette, bits=2)
                (txb, tyb) = self.next_tile(txb, tyb, width, height)
            elif code == 15:
                (txb, tyb) = self.read_coordinates(bs)
                palette = self.read_palette(bs, colours, 4)
                yield txb, tyb, self.read_tile(bs, palette, bits=2)
                (txb, tyb) = self.next_tile(txb, tyb, width, height)
            elif code == 13:
                (txb, tyb) = self.read_coordinates(bs)
                palette = self.read_palette(bs, colours, 1)
                yield txb, tyb, self.read_tile(bs, palette, bits=0)
                (txb, tyb) = self.next_tile(txb, tyb, width, height)
            elif code == 14:
                (txb, tyb) = self.read_coordinates(bs)
                palette = self.read_palette(bs, colours, 2)
                yield txb, tyb, self.read_tile(bs, palette, bits=1)
                (txb, tyb) = self.next_tile(txb, tyb, width, height)
            else:
                raise ValueError("Unknown code: %d\n" % code)
