from contextlib import AsyncExitStack, asynccontextmanager

import httpx

from pydantic_ai._agent_graph import GraphAgentState
from pydantic_ai.agent import AbstractAgent

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    PartDeltaEvent,
    PartEndEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    UserPromptPart,
)
from pydantic_ai.run import AgentRunResult, AgentRunResultEvent

from a2a.client import ClientConfig, create_client
from a2a.helpers import get_artifact_text, get_message_text, new_text_message
from a2a.types import Role, SendMessageRequest


def _last_user_text(messages):

    for message in reversed(list(messages or [])):
        if isinstance(message, ModelRequest):

            for part in reversed(message.parts):
                if isinstance(part, UserPromptPart) and isinstance(part.content, str):

                    return part.content

    return ''


class RemoteAgent(AbstractAgent):

    def __init__(self, spec, card, *, name=None, description=None):

        self._name = name or 'Remote Agent'
        self._description = spec.description or description or self._name

        self._card = card

        self._base_url = str(spec.url)
        self._timeout = spec.timeout

        self._stack, self._httpx, self._client = None, None, None

    @property
    def model(self): return None

    @property
    def name(self): return self._name

    @name.setter
    def name(self, value): self._name = value

    @property
    def description(self): return self._description

    @description.setter
    def description(self, value): self._description = value

    @property
    def card(self): return self._card

    @property
    def deps_type(self): return type(None)

    @property
    def output_type(self): return str

    @property
    def event_stream_handler(self): return None

    @property
    def toolsets(self): return []

    def iter(self, *args, **kwargs):
        raise NotImplementedError

    def override(self, **kwargs):
        raise NotImplementedError

    async def __aenter__(self):

        self._stack = AsyncExitStack()

        timeout = httpx.Timeout(
                connect=5.0, read=self._timeout, write=10.0, pool=5.0)

        self._httpx = await self._stack.enter_async_context(
                httpx.AsyncClient(timeout=timeout))

        return self

    async def __aexit__(self, *args):

        if self._stack is not None:
            await self._stack.aclose()

        self._stack = self._httpx = self._client = None
        return False

    def render_description(self):
        return self._description

    async def _create_client(self):

        client_config = ClientConfig(
                streaming=True, httpx_client=self._httpx)

        self._client = await create_client(
                agent=self._base_url, client_config=client_config)

        self._stack.push_async_callback(self._client.close)

        return self._client

    async def _stream_a2a(self, prompt):

        client = self._client or await self._create_client()

        req = SendMessageRequest(
            message=new_text_message(prompt, role=Role.ROLE_USER))

        async for res in client.send_message(req):

            kind = res.WhichOneof('payload')

            if kind == 'artifact_update':
                text = get_artifact_text(res.artifact_update.artifact)

            elif kind == 'message':
                text = get_message_text(res.message)

            else:
                continue

            if text:
                yield text


    def run_stream_events(
            self, user_prompt=None, *, message_history=None, **kwargs):

        prompt = (user_prompt if isinstance(user_prompt, str)
                  else _last_user_text(message_history))

        async def events():

            started, chunks = False, []

            async for v in self._stream_a2a(prompt):

                if not started:
                    yield PartStartEvent(index=0, part=TextPart(''))
                    started = True

                chunks.append(v)

                yield PartDeltaEvent(
                        index=0, delta=TextPartDelta(content_delta=v))

            text = ''.join(chunks)

            if not started:
                yield PartStartEvent(index=0, part=TextPart(''))

            yield PartEndEvent(index=0, part=TextPart(text))

            state = GraphAgentState(
                message_history=[
                    ModelRequest(parts=[UserPromptPart(content=prompt)]),
                    ModelResponse(parts=[TextPart(text)]),
                ]
            )

            yield AgentRunResultEvent(AgentRunResult(text, _state=state))

        @asynccontextmanager
        async def stream():
            yield events()

        return stream()

    async def run(self, user_prompt, **kwargs):

        text = ''.join([v async for v in self._stream_a2a(user_prompt)])

        state = GraphAgentState(
            message_history=[
                ModelRequest(parts=[UserPromptPart(content=user_prompt)]),
                ModelResponse(parts=[TextPart(text)]),
            ]
        )

        return AgentRunResult(text, _state=state)

    @classmethod
    def from_spec(cls, spec, card, *, name=None, description=None):
        return cls(spec, card, name=name, description=description)


