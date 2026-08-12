
from contextlib import AsyncExitStack, asynccontextmanager

import httpx

from fasta2a.pydantic_ai import agent_to_a2a 

from fastapi.responses import StreamingResponse

from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route, get_route_path

from ..settings import RemoteSettings


class _A2A:

    def __init__(self, local_agents, remote_specs, *, base_url, max_hop):

        self._base_url = base_url

        self._hop_header = RemoteSettings.hop_header
        self._drop_headers = RemoteSettings.drop_headers

        self._max_hop = max_hop

        self._local_agents = {k: self._make_local_agent(k, v)
                              for k, v in local_agents.items()}

        self._remote_agents = {k: self._make_remote_agent(k, v)
                               for k, v in remote_specs.items()}

        self._agents = {**self._local_agents, **self._remote_agents}

        self._app = self._build_app()

    @property
    def app(self):
        return self._app

    def _make_local_agent(self, agent_name, agent):

        description = agent.render_description() or agent_name

        url = f'{self._base_url}/a2a/{agent_name}'

        return agent_to_a2a(
                agent, name=agent_name, url=url, description=description)

    def _make_remote_agent(self, agent_name, spec):

        url = f'{self._base_url}/a2a/{agent_name}'

        # rewrite
        async def rewrite(request):

            hop = int(request.headers.get(self._hop_header, 0))

            if hop >= self._max_hop:
                return JSONResponse(
                        {'error': f'gentleman: hop limit exceeded ({hop})'},
                        status_code=508)

            headers = {self._hop_header: str(hop + 1)}

            try:
                res = await request.app.state.client.get(
                        f'{spec.url}/.well-known/agent-card.json',
                        headers=headers)

                if res.status_code == 508:
                    return JSONResponse(res.json(), status_code=508)

                res.raise_for_status()
                card = res.json()

            except (httpx.HTTPError, ValueError) as err:
                return JSONResponse({'error': str(err)}, status_code=502)

            description = (spec.description
                           or card.get('description') or agent_name)

            card = {**card, 'name': agent_name,
                    'url': url, 'description': description}

            for v in card.get('additionalInterfaces') or []:
                v['url'] = url

            return JSONResponse(card)

        # relay
        async def relay(request):

            hop = int(request.headers.get(self._hop_header, 0))

            if hop >= self._max_hop:
                return JSONResponse(
                        {'error': f'gentleman: hop limit exceeded ({hop})'},
                        status_code=508)

            headers = {k: v for k, v in request.headers.items()
                       if k.lower() not in self._drop_headers}

            headers = {**headers, self._hop_header: str(hop + 1)}

            c = request.app.state.client
            p = get_route_path(request.scope)

            req = c.build_request(request.method,
                                  f'{spec.url}{p}',
                                  params=request.query_params,
                                  headers=headers,
                                  content=await request.body())

            res = await c.send(req, stream=True)

            headers = {k: v for k, v in res.headers.items()
                       if k.lower() not in self._drop_headers}

            return StreamingResponse(res.aiter_raw(),
                                     status_code=res.status_code,
                                     headers=headers,
                                     background=BackgroundTask(res.aclose))

        @asynccontextmanager
        async def lifespan(app):

            async with httpx.AsyncClient(headers=spec.headers,
                                         timeout=spec.timeout,
                                         follow_redirects=True) as c:

                app.state.client = c
                yield

        routes = [Route('/.well-known/agent-card.json', rewrite),
                  Route('/{path:path}', relay, methods=['GET', 'POST'])]

        return Starlette(lifespan=lifespan, routes=routes)

    def _build_app(self):
        routes = [Mount(f'/{k}', app=v) for k, v in self._agents.items()]
        return Starlette(routes=routes)

    @asynccontextmanager
    async def lifespan(self):

        async with AsyncExitStack() as stack:

            for v in self._agents.values():
                await stack.enter_async_context(v.router.lifespan_context(v))

            yield


def create_a2a(local_agents, remote_specs, *, base_url, max_hop):

    a2a = _A2A(
            local_agents, remote_specs, base_url=base_url, max_hop=max_hop)

    return a2a


