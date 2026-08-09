import asyncio
from uuid import uuid4

from contextlib import asynccontextmanager

import httpx

from a2a.client import A2ACardResolver, ClientFactory, ClientConfig

from a2a.types import (Task, TaskQueryParams, TaskState ,
                       Message, Part, Role, TextPart)

from pydantic_ai import Tool

from fasta2a.pydantic_ai import agent_to_a2a 

from fastapi.responses import StreamingResponse

# ag-ui proxy
from ag_ui.core import (EventType, RunAgentInput,
                        RunErrorEvent, RunFinishedEvent,
                        RunStartedEvent, TextMessageContentEvent,
                        TextMessageEndEvent, TextMessageStartEvent)

from ag_ui.encoder import EventEncoder

# a2a proxy
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse
from starlette.routing import Route, get_route_path

# a2a client
terminal = {TaskState.completed, TaskState.failed,
            TaskState.canceled, TaskState.rejected}


def _user_message(prompt):

    return Message(role=Role.user,
                   parts=[Part(root=TextPart(text=prompt))],
                   message_id=uuid4().hex)


def _extract_text(obj):

    texts = []
 
    if isinstance(obj, Message):

        for v in obj.parts or []:
            root = getattr(v, 'root', v)

            if isinstance(root, TextPart):
                texts.append(root.text)

    elif isinstance(obj, Task):

        for v1 in obj.artifacts or []:

            for v2 in v1.parts or []:
                root = getattr(v2, 'root', v2)

                if isinstance(root, TextPart):
                    texts.append(root.text)

        if not texts and obj.status and obj.status.message:
            texts.append(_extract_text(obj.status.message))
 
    return '\n'.join(v for v in texts if v)


def make_tool(name, config):

    return Tool(make_ask(config),
                name=f'ask_{name}',
                description=config.description or name)


def make_ask(config, extra_headers=None):

    async def ask(prompt):

        headers = {**(config.headers or {}), **(extra_headers or {})}

        async with httpx.AsyncClient(headers=headers,
                                     timeout=config.timeout,
                                     follow_redirects=True) as c:

            resolver = A2ACardResolver(httpx_client=c,
                                       base_url=str(config.url))

            client = ClientFactory(ClientConfig(httpx_client=c)
                                   ).create(await resolver.get_agent_card())

            task = None

            async for v in client.send_message(_user_message(prompt)):
                if isinstance(v, Message):
                    return _extract_text(v)

                task = v[0] if isinstance(v, tuple) else v

            while task is not None and task.status.state not in terminal:
                await asyncio.sleep(1)
                task = await client.get_task(TaskQueryParams(id=task.id))

            return _extract_text(task) if task else '(no response received)'

    return ask



# a2a proxy
X_GENTLEMAN_HOP ='x-gentleman-hop'

drop_headers = {'host', 'content-length',
                'transfer-encoding', 'connection'}

def make_a2a_proxy(name, config, url, max_hop):

    @asynccontextmanager
    async def lifespan(app):

        async with httpx.AsyncClient(headers=config.headers,
                                     timeout=config.timeout,
                                     follow_redirects=True) as c:

            app.state.client = c
            yield


    async def agent_card(request):

        hop = int(request.headers.get(X_GENTLEMAN_HOP , 0))

        if hop >= max_hop:
            return JSONResponse(
                    {'error': f'gentleman: hop limit exceeded ({hop})'},
                    status_code=508)

        headers = {X_GENTLEMAN_HOP: str(hop + 1)}

        try:
            res = await request.app.state.client.get(
                    f'{config.url}/.well-known/agent-card.json',
                    headers=headers)

            if res.status_code == 508:
                return JSONResponse(res.json(), status_code=508)

            res.raise_for_status()
            card = res.json()

        except Exception as err:
            return JSONResponse({'error': str(err)}, status_code=502)

        card = {**card, 'name': name,
                        'url': url,
                        'description': (config.description or
                                        card.get('description') or name)}

        for v in card.get('additionalInterfaces') or []:
            v['url'] = url

        return JSONResponse(card)


    async def proxy(request):

        hop = int(request.headers.get(X_GENTLEMAN_HOP , 0))

        if hop >= max_hop:
            return JSONResponse(
                    {'error': f'gentleman: hop limit exceeded ({hop})'},
                    status_code=508)

        headers = {k: v for k, v in request.headers.items()
                   if k.lower() not in drop_headers}

        headers = {**headers,
                   **(config.headers or {}),
                   X_GENTLEMAN_HOP: str(hop + 1)}

        c = request.app.state.client
        p = get_route_path(request.scope)

        req = c.build_request(request.method,
                              f'{config.url}{p}',
                              params=request.query_params,
                              headers=headers,
                              content=await request.body())

        res = await c.send(req, stream=True)

        headers = {k: v for k, v in res.headers.items()
                   if k.lower() not in drop_headers}

        return StreamingResponse(res.aiter_raw(),
                                 status_code=res.status_code,
                                 headers=headers,
                                 background=BackgroundTask(res.aclose))


    return Starlette(
            lifespan=lifespan,
            routes=[Route('/.well-known/agent-card.json', agent_card),
                    Route('/{path:path}', proxy, methods=['GET', 'POST'])])


# ag-ui proxy
def _last_user_text(messages):

    for v in reversed(messages):
        if v.role == 'user':
            return v.content

    return ''


def make_agui_proxy(config, max_hop):

    async def handle(request):

        hop = int(request.headers.get(X_GENTLEMAN_HOP , 0))

        if hop >= max_hop:
            return JSONResponse(
                    {'error': f'gentleman: hop limit exceeded ({hop})'},
                    status_code=508)

        ask = make_ask(config, {X_GENTLEMAN_HOP: str(hop + 1)})

        input = RunAgentInput.model_validate(await request.json())

        async def events():

            encode = EventEncoder().encode
            message_id = uuid4().hex

            yield encode(RunStartedEvent(type=EventType.RUN_STARTED,
                                         thread_id=input.thread_id,
                                         run_id=input.run_id))

            yield encode(TextMessageStartEvent(type=EventType.TEXT_MESSAGE_START,
                                               message_id=message_id,
                                               role='assistant'))

            try:
                answer = await ask(_last_user_text(input.messages))

            except (Exception) as err:
                yield encode(RunErrorEvent(type=EventType.RUN_ERROR,
                                           message=str(err)))

                return

            if answer:
                yield encode(TextMessageContentEvent(type=EventType.TEXT_MESSAGE_CONTENT,
                                                     message_id=message_id,
                                                     delta=answer))

            yield encode(TextMessageEndEvent(type=EventType.TEXT_MESSAGE_END,
                                             message_id=message_id))

            yield encode(RunFinishedEvent(type=EventType.RUN_FINISHED,
                                          thread_id=input.thread_id,
                                          run_id=input.run_id))

        return StreamingResponse(events(), media_type='text/event-stream')

    return handle


# a2a server
def build_a2a(agents, remotes, base_url, max_hop):

    a2a = {k: agent_to_a2a(v,
                           name=k,
                           url=f'{base_url}/a2a/{k}',
                           description=v.render_description() or k)

              for k, v in agents.items()}


    a2a.update({k: make_a2a_proxy(k, v, f'{base_url}/a2a/{k}', max_hop)
                   for k, v in remotes.items()})

    return a2a


