from fastapi import APIRouter, Depends, HTTPException, Request, Response

from pydantic_ai.ui.ag_ui import AGUIAdapter

from ..settings import RemoteSettings
from ..core import hop


__all__ = ['agui_path_prefix', 'create_agui', 'create_agui_router']


agui_path_prefix = _path_prefix = '/agents'


class _AGUI:

    def __init__(self, agents, *, max_hop):

        self._max_hop = max_hop

        self._agents = agents

        # router
        self._router = self._build_router()

    @property
    def router(self):
        return self._router

    def _build_router(self):

        router = APIRouter(dependencies=[
            Depends(hop.make_check(self._max_hop))])

        @router.post(f'{_path_prefix}/{{agent_name}}')
        async def agui_chat(agent_name: str, request: Request) -> Response:

            if (agent := self._agents.get(agent_name)) is None:
                detail = f'gentleman: unknown agent {agent_name!r}'
                raise HTTPException(status_code=404, detail=detail)

            return await AGUIAdapter.dispatch_request(request, agent=agent)

        return router


def create_agui(agents, *, max_hop):

    agui = _AGUI(agents, max_hop=max_hop)
    return agui


def create_agui_router(agents, *, max_hop):

    router = _AGUI(agents, max_hop=max_hop).router
    return router


