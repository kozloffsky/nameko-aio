import asyncio
import aiormq
import uuid
import json

RPC_QUEUE_TEMPLATE = 'rpc-{}'
RPC_REPLY_QUEUE_TEMPLATE = 'rpc.reply-{}-{}'
RPC_REPLY_QUEUE_TTL = 300000  # ms (5 mins)
RPC_EXCHANGE_NAME = 'nameko-rpc'

async def get_rpc_exchange():
    connnection = await aiormq.connect("amqp://rabbitmq:rabbitmq@localhost/")
    channel = await connnection.channel()
    await channel.exchange_declare(RPC_EXCHANGE_NAME, exchange_type='topic', durable=True)
    return channel

class MethodProxy:
    def __init__(self, service_name, method_name, rpc):
        self.service_name = service_name
        self.method_name = method_name
        self.rpc = rpc

    async def __call__(self, *args, **kwargs):
        payload = {'args':args, 'kwargs':kwargs}
        return await self.rpc.call(self.service_name, self.method_name, payload)


class ServiceProxy:
    def __init__(self, service_name, rpc):
        self.service_name = service_name
        self.rpc = rpc

    def __getattr__(self, name):
        return MethodProxy(
            self.service_name,
            name,
            self.rpc
        )

class RpcProxy:
    
    def __init__(self):
        self.connnection = None
        self.futures = {}
        self.reply_to = None
        self.routing_key = None


    async def connect(self):
        channel = await get_rpc_exchange()
        reply_queue_uuid = uuid.uuid4()
        queue_name = RPC_REPLY_QUEUE_TEMPLATE.format('asyncio-nameko-proxy', uuid.uuid4())

        queue = await channel.queue_declare(queue_name, auto_delete=True)
        self.reply_to = queue.queue
        self.routing_key = str(reply_queue_uuid)

        await channel.queue_bind(queue.queue, RPC_EXCHANGE_NAME, routing_key=str(reply_queue_uuid))
        await channel.basic_consume(self.reply_to, self.handle_message)
        return self


    async def handle_message(self, message: aiormq.types.DeliveredMessage):
        correlation_id = message.header.properties.correlation_id
        future = self.futures.pop(correlation_id)
        result = json.loads(message.body)
        if result['error'] is not None:
            return future.set_exception(Exception(result['error']))
        future.set_result(result)


    async def call(self, service_name, method_name, msg):
        channel = await get_rpc_exchange()
        correlation_id = str(uuid.uuid4())
        routing_key = "{}.{}".format(service_name,method_name)
        
        future = asyncio.get_running_loop().create_future()

        self.futures[correlation_id] = future

        await channel.basic_publish(
            json.dumps(msg).encode(), routing_key=routing_key, mandatory=True,
            exchange=RPC_EXCHANGE_NAME,
            properties = aiormq.spec.Basic.Properties(
                correlation_id=correlation_id,
                reply_to=self.routing_key,
                content_type='application/json'
            ))
        return await future

    def __getattr__(self, name):
        return ServiceProxy(name, self)