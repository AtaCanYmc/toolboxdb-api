import asyncio
from unittest.mock import AsyncMock, MagicMock


async def main():
    redis_mock = MagicMock()
    pipe_mock = AsyncMock()
    pipe_mock.execute.return_value = [True, 1]

    ctx_manager = MagicMock()
    ctx_manager.__aenter__.return_value = pipe_mock

    redis_mock.pipeline.return_value = ctx_manager

    async with redis_mock.pipeline(transaction=True) as pipe:
        pipe.set("key", 0, nx=True)
        pipe.incr("key")
        res = await pipe.execute()
        print(res)


asyncio.run(main())
