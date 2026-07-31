import asyncio
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, ClientFactory, ClientConfig
from a2a.types import Task, TaskQueryParams, TaskState, Message, Part, Role, TextPart

from pydantic_ai import Tool

from fasta2a.pydantic_ai import agent_to_a2a 

from fastapi.responses import StreamingResponse

from ag_ui.core import (EventType, RunAgentInput,
                        RunErrorEvent, RunFinishedEvent,
                        RunStartedEvent, TextMessageContentEvent,
                        TextMessageEndEvent, TextMessageStartEvent)

from ag_ui.encoder import EventEncoder

# a2a client
terminal = {TaskState.completed,TaskState.failed,
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


def fetch_agent_card(config):

    with httpx.Client(headers=config.headers, timeout=config.timeout) as c:

        res = c.get(f'{config.url}/.well-known/agent-card.json')
        res.raise_for_status()

        return res.json()


def _make_ask(config):

    async def ask(prompt):

        async with httpx.AsyncClient(headers=config.headers,
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


def make_remote_tool(name, config):

    card = fetch_agent_card(config)
    description = config.description or card.get('description') or name

    return Tool(_make_ask(config), name=f'ask_{name}', description=description)


# ag-ui proxy
def _last_user_text(messages):

    for v in reversed(messages):
        if v.role == 'user':
            return v.content

    return ''


def make_agui_proxy(config):

    ask = _make_ask(config)

    async def handle(request):

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
def build_a2a(agents, base_url):

    a2a = {
        k: agent_to_a2a(v,
                        name=k,
                        url=f'{base_url}/a2a/{k}',
                        description=v.render_description() or k)

        for k, v in agents.items()
    }

    return a2a


