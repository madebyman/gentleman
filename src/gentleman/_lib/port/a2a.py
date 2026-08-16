from a2a.helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_status_update_event,
    new_text_artifact_update_event,
)

from a2a.server.agent_execution import AgentExecutor
from a2a.server.routes.jsonrpc_dispatcher import JsonRpcDispatcher
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.request_handlers.response_helpers import agent_card_to_dict
from a2a.server.tasks import TaskUpdater, InMemoryTaskStore
from a2a.types import TaskState

from pydantic_ai.messages import (
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
)

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from ..settings import RemoteSettings


a2a_path_prefix = _path_prefix = '/a2a'

_ARTIFACT_NAME = 'response'


async def _iter_response(agent, prompt):

    print('ok')
    async with agent.run_stream_events(prompt) as events:

        async for v in events:

            if (isinstance(v, PartStartEvent)
                and isinstance(v.part, TextPart)):

                if v.part.content:
                    yield v.part.content

            elif (isinstance(v, PartDeltaEvent)
                  and isinstance(v.delta, TextPartDelta)):

                if v.delta.content_delta:
                    yield v.delta.content_delta


class _A2AAgentExecutor(AgentExecutor):

    def __init__(self, agent):
        self._agent = agent

    async def execute(self, context, event_queue):

        task = context.current_task or new_task_from_user_message(context.message)

        await event_queue.enqueue_event(task)


        await event_queue.enqueue_event(
            new_text_status_update_event(task_id=task.id,
                                         context_id=task.context_id,
                                         state=TaskState.TASK_STATE_WORKING,
                                         text='working'))

        prompt = get_message_text(context.message)

        try:
            async for v in _iter_response(self._agent, prompt):

                await event_queue.enqueue_event(
                    new_text_artifact_update_event(task_id=task.id,
                                                   context_id=task.context_id,
                                                   name=_ARTIFACT_NAME,
                                                   text=v))

        except (Exception) as err:
            await event_queue.enqueue_event(
                new_text_status_update_event(task_id=task.id,
                                             context_id=task.context_id,
                                             state=TaskState.TASK_STATE_FAILED,
                                             text=f'gentleman: {err}'))
            return

        await event_queue.enqueue_event(
            new_text_status_update_event(task_id=task.id,
                                         context_id=task.context_id,
                                         state=TaskState.TASK_STATE_COMPLETED,
                                         text='done'))

    async def cancel(
            self, context: RequestContext, event_quere: EventQueue):
        raise NotImplementedError


class _A2A:

    def __init__(self, agents, *, max_hop):

        self._hop_header = RemoteSettings.hop_header
        self._max_hop = max_hop

        self._agents = agents

        self._dispatchers = {}

        for k, v in self._agents.items():

            request_handler = DefaultRequestHandler(
                    agent_executor=_A2AAgentExecutor(v),
                    task_store=InMemoryTaskStore(),
                    agent_card=v.card)

            self._dispatchers[k] = JsonRpcDispatcher(
                    request_handler=request_handler)

        # router
        self._router = self._build_router()

    @property
    def router(self):
        return self._router

    def _build_router(self):

        router = APIRouter()

        @router.get(f'{_path_prefix}/{{agent_name}}/.well-known/agent-card.json')
        async def a2a_agent_card(agent_name: str, request: Request) -> Response:

            if (agent := self._agents.get(agent_name)) is None:
                raise HTTPException(
                        status_code=404, detail=f'gentleman: unknown agent {agent_name!r}')

            return JSONResponse(agent_card_to_dict(agent.card))

        @router.post(f'{_path_prefix}/{{agent_name}}')
        async def a2a_rpc(agent_name: str, request: Request) -> Response:

            if (dispatcher := self._dispatchers.get(agent_name)) is None:
                raise HTTPException(
                        status_code=404, detail=f'gentleman: unknown agent {agent_name!r}')

            return await dispatcher.handle_requests(request)

        return router


def create_a2a_router(agents, *, max_hop):

    router = _A2A(agents, max_hop=max_hop).router
    return router


