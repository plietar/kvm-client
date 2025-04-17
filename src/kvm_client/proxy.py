import asyncio
import functools
import ssl
from typing import Any, Coroutine


async def copy_stream(
    input: asyncio.StreamReader, output: asyncio.StreamWriter, chunksize: int = 1024
) -> None:
    while True:
        data = await input.read(chunksize)
        if not data:
            break

        output.write(data)
        try:
            await output.drain()
        except ConnectionResetError:
            break


async def race_tasks(*coroutines: Coroutine[Any, Any, None]) -> None:
    """
    Run a collection of coroutines as tasks, concurrently, until at least
    one of them completes or terminates with an exception. All uncompleted tasks
    will then be cancelled.

    If one or more tasks raise an error other than `asyncio.CancelledError`, a
    TaskGroupError containing all of them is raised.
    """
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(a) for a in coroutines]
        (done, pending) = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # The default TaskGroup behaviour is to wait for all child tasks on
        # exit. What we actually want to do is cancel anything that is
        # remaining.
        for t in pending:
            t.cancel()


async def proxy_connection(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    *,
    hostname: str,
    ssl: ssl.SSLContext,
) -> None:
    try:
        upstream_reader, upstream_writer = await asyncio.open_connection(
            hostname, port=443, ssl=ssl
        )

        try:
            await race_tasks(
                copy_stream(reader, upstream_writer),
                copy_stream(upstream_reader, writer),
            )
        finally:
            upstream_writer.close()
            await upstream_writer.wait_closed()
    finally:
        writer.close()
        await writer.wait_closed()


async def proxy(hostname: str, port: int, ssl: ssl.SSLContext) -> None:
    on_connection = functools.partial(proxy_connection, hostname=hostname, ssl=ssl)
    server = await asyncio.start_server(on_connection, port=port)
    async with server:
        await server.serve_forever()
