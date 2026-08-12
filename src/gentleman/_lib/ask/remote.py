import asyncio
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, ClientFactory, ClientConfig
from a2a.types import (Task, TaskQueryParams,
                       TaskState, Message,
                       Part, Role, TextPart)

from pydantic_ai import Tool


_terminal = {TaskState.completed, TaskState.failed,
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


# make_ask
def make_ask(spec, *, extra_headers=None):

    async def ask(prompt):

        headers = {**(spec.headers or {}), **(extra_headers or {})}

        async with httpx.AsyncClient(headers=headers,
                                     timeout=spec.timeout,
                                     follow_redirects=True) as c:

            resolver = A2ACardResolver(httpx_client=c,
                                       base_url=str(spec.url))

            client = ClientFactory(ClientConfig(httpx_client=c)
                                   ).create(await resolver.get_agent_card())

            task = None

            async for v in client.send_message(_user_message(prompt)):

                if isinstance(v, Message):
                    return _extract_text(v) or '(no text content in response)'

                task = v[0] if isinstance(v, tuple) else v

            while task is not None and task.status.state not in _terminal:
                await asyncio.sleep(1)
                task = await client.get_task(TaskQueryParams(id=task.id))

            if task is None:
                return '(no response received)'

            return _extract_text(task) or '(no text content in response)'

    return ask


# make_tool
def make_tool(agent_name, spec):

    return Tool(make_ask(spec),
                name=f'ask_{agent_name}',
                description=spec.description or agent_name)


