from uuid import uuid4

from ag_ui.core import (EventType,
                        RunAgentInput,
                        RunErrorEvent,
                        RunFinishedEvent,
                        RunStartedEvent,
                        TextMessageContentEvent,
                        TextMessageEndEvent,
                        TextMessageStartEvent)

from ag_ui.encoder import EventEncoder

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from pydantic_ai.ui.ag_ui import AGUIAdapter

from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from ..ask import remote
from ..settings import RemoteSettings


def _last_user_text(messages):

    for v in reversed(messages):
        if v.role == 'user':
            return v.content

    return ''


class _AGUI:

    def __init__(self, local_agents, remote_specs, *, max_hop):

        self._hop_header = RemoteSettings.hop_header
        self._max_hop = max_hop

        self._local_agents = local_agents
        self._remote_specs = remote_specs

        self._remote_agents = {k: self._make_remote_agent(k, v)
                               for k, v in remote_specs.items()}

        # router
        self._router = self._build_router()

    @property
    def router(self):
        return self._router

    async def _events(self, ask, input):

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

    def _make_remote_agent(self, agent_name, spec):

        async def handle(request):

            hop = int(request.headers.get(self._hop_header, 0))

            if hop >= self._max_hop:
                return JSONResponse(
                        {'error': f'gentleman: hop limit exceeded ({hop})'},
                        status_code=508)

            ask = remote.make_ask(
                    spec, extra_headers={self._hop_header: str(hop + 1)})

            input = RunAgentInput.model_validate(await request.json())

            return StreamingResponse(self._events(ask, input),
                                     media_type='text/event-stream')

        return handle

    def _build_router(self):

        router = APIRouter()

        @router.post('/agents/{agent_name}')
        async def agui(agent_name: str, request: Request) -> Response:
            return await self._dispatch(agent_name, request)

        return router

    async def _dispatch(self, agent_name, request):

        # local
        if (agent := self._local_agents.get(agent_name)) is not None:
            return await AGUIAdapter.dispatch_request(request, agent=agent)

        # remote
        if (handle := self._remote_agents.get(agent_name)) is not None:
            return await handle(request)

        raise HTTPException(404)


def create_agui_router(local_agents, remote_specs, *, max_hop):

    router = _AGUI(local_agents, remote_specs, max_hop=max_hop).router
    return router


