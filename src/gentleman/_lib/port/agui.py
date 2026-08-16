from fastapi import APIRouter, HTTPException, Request, Response

from pydantic_ai.ui.ag_ui import AGUIAdapter

from ..settings import RemoteSettings


agui_path_prefix = _path_prefix = '/agents'


class _AGUI:

    def __init__(self, agents, *, max_hop):

        self._hop_header = RemoteSettings.hop_header
        self._max_hop = max_hop

        self._agents = agents

        # router
        self._router = self._build_router()

    @property
    def router(self):
        return self._router

    def _build_router(self):

        router = APIRouter()

        @router.post(f'{_path_prefix}/{{agent_name}}')
        async def agui_chat(agent_name: str, request: Request) -> Response:

            if (agent := self._agents.get(agent_name)) is None:
                raise HTTPException(
                        status_code=404, detail=f'gentleman: unknown agent {agent_name!r}')

            return await AGUIAdapter.dispatch_request(request, agent=agent)

        return router


def create_agui_router(agents, *, max_hop):

    router = _AGUI(agents, max_hop=max_hop).router
    return router


