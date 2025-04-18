import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "true"

import asyncio
import functools
from typing import Awaitable, Callable, Any, Coroutine

import click
import pygame

from . import gui, proxy, web
from .kvm import KVM


def asyncio_main[**P](f: Callable[P, Coroutine[Any, Any, None]]) -> Callable[P, None]:
    @functools.wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            asyncio.run(f(*args, **kwargs))
        except KeyboardInterrupt:
            pass

    return wrapper


async def periodic(f: Callable[..., Awaitable[None | bool]], period: float) -> None:
    while True:
        if await f() is False:
            break
        await asyncio.sleep(period)


async def redraw(surface: pygame.Surface, output: gui.PyGameOutput) -> None:
    if output.surface is not None:
        if output.size != surface.get_size() and output.size != (0, 0):
            pygame.display.set_mode(output.size)
        surface.blit(output.surface, (0, 0))
    else:
        surface.fill((0, 0, 0))

    pygame.display.update()


@click.group()
def main() -> None:
    pass


async def main_loop(params: web.ConnectionParameters) -> None:
    pygame.init()
    surface = pygame.display.set_mode((500, 500))

    print("Connecting to KVM")

    output = gui.PyGameOutput()
    try:
        async with KVM(params.hostname, params.port, params.token, output) as kvm:
            await proxy.race_tasks(
                kvm.loop(),
                periodic(functools.partial(gui.handle_events, kvm), 0.001),
                periodic(functools.partial(redraw, surface, output), 1 / 30),
            )
    except BaseException as e:
        print(e)
        raise


@main.command("connect")
@click.argument("hostname")
@click.option("--username", required=True, default="root")
@click.option("--password", required=True)
def cli_connect(hostname: str, username: str, password: str) -> None:
    print("Logging in")
    cookie = web.login(hostname, username, password)
    params = web.get_kvm_parameters(hostname, cookie)

    asyncio.run(main_loop(params))


@main.command("proxy")
@click.argument("hostname")
@click.option("--port", default=8080, type=int)
@asyncio_main
async def cli_proxy(hostname: str, port: int) -> None:
    await proxy.proxy(hostname, port, ssl=web.ctx)
