import asyncio
import aiormq
import uuid
import json
from namekoaio.rpc import RpcProxy 


async def main():
    proxy = RpcProxy()
    await proxy.connect()
    print(await proxy.guard.get_user_permissions("adfsdfsd"))


loop = asyncio.get_event_loop()
loop.run_until_complete(main())