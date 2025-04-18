import numpy as np
import numpy.typing as npt

from contextlib import contextmanager
from typing import Iterator, Self
from . import kvm
from . import asp2000
import simplejpeg


class JPEGOutput(kvm.KVMOutput[asp2000.YUV], kvm.KVMUpdater[asp2000.YUV]):
    Y: npt.NDArray[np.uint8]
    U: npt.NDArray[np.uint8]
    V: npt.NDArray[np.uint8]

    def __init__(self) -> None:
        self.Y = np.ndarray((0, 0), dtype=np.uint8)
        self.U = np.ndarray((0, 0), dtype=np.uint8)
        self.V = np.ndarray((0, 0), dtype=np.uint8)

    @contextmanager
    def update(self, width: int, height: int) -> Iterator[Self]:
        if self.Y.shape != (height, width):
            self.Y = np.ndarray((height, width), dtype=np.uint8)
            self.U = np.ndarray((height, width), dtype=np.uint8)
            self.V = np.ndarray((height, width), dtype=np.uint8)
        yield self

    def update_rect(self, x: int, y: int, data: list[asp2000.YUV]) -> None:
        for i in range(8):
            for j in range(8):
                self.Y[y * 8 + j, x * 8 + i] = data[i + j * 8][0]
                self.U[y * 8 + j, x * 8 + i] = data[i + j * 8][1]
                self.V[y * 8 + j, x * 8 + i] = data[i + j * 8][2]

    def decode_color(self, color: asp2000.YUV) -> asp2000.YUV:
        return color

    def has_image(self) -> bool:
        return self.Y.shape != (0, 0)

    def encode(self) -> bytes:
        return simplejpeg.encode_jpeg_yuv_planes(self.Y, self.U, self.V)


async def capture(params: kvm.ConnectionParameters) -> bytes:
    output = JPEGOutput()
    async with kvm.KVM(params, output) as conn:
        while True:
            await conn.poll()
            if output.has_image():
                return output.encode()
