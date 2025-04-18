import itertools

import pygame

from . import asp2000
from .kvm import KVM, KVMOutput


def parse_yuv(y: int, u: int, v: int) -> pygame.Color:
    # https://softpixel.com/~cwright/programming/colorspace/yuv/
    r = y + 1.4075 * (v - 128)
    g = y - 0.3455 * (u - 128) - (0.7169 * (v - 128))
    b = y + 1.7790 * (u - 128)
    return pygame.Color(int(r), int(g), int(b))


class PyGameOutput(KVMOutput):
    size: tuple[int, int]
    surface: pygame.Surface

    def __init__(self) -> None:
        self.size = (0, 0)
        self.surface = pygame.Surface(self.size)

    def update_size(self, width: int, height: int) -> None:
        size = (width, height)
        if self.size != size:
            self.size = size
            self.surface = pygame.Surface(size)

    def update_rect(self, x: int, y: int, data: list[asp2000.YUV]) -> None:
        with pygame.PixelArray(self.surface) as array:
            # pygame doesn't have anything to assign a rectangle as one operation.
            # We have to iterate over rows
            for i in range(8):
                array[x*8:(x+1)*8, y*8+i] = [parse_yuv(*c) for c in data[8*i:8*(i+1)]]


async def handle_events(kvm: KVM) -> bool | None:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        elif event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
            keys = pygame.key.get_pressed()
            keys_set = list(itertools.compress(range(len(keys)), keys))
            await kvm.send_keys(keys_set)
    return None
