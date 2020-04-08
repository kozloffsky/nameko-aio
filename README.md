# Nameko-aio

asyncronous proxy for nameko services for use with async/await and event loops

example:

```python
    async def main():
        proxy = RpcProxy()
        await proxy.connect()
        print(await proxy.guard.get_user_permissions("some_user_id"))


    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
```
