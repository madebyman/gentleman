import functools

from contextvars import ContextVar
from dataclasses import dataclass, replace

from fastapi import Request, HTTPException
from starlette.datastructures import Headers


HEADER = 'x-gentleman-hop'


@dataclass(frozen=True, slots=True)
class Context:
    hop: int = 0
    correlation_id: str | None = None


_current = ContextVar('gentleman.hop_context', default=Context())


def current_hop():
    return _current.get().hop


def _parse_hop(raw):
    if raw is None or not raw.isdigit():
        return 0

    return int(raw)


class Guard:

    def __init__(self, app, max_hop):
        self._app = app
        self._max_hop = max_hop

    async def __call__(self, scope, receive, send):

        if scope['type'] != 'http':
            await self._app(scope, receive, send)
            return

        hop = _parse_hop(Headers(scope=scope).get(HEADER))

        if hop >= self._max_hop:
            detail = f'gentleman: hop limit exceeded ({hop} >= {max_hop})' 
            await PlainTextResponse(
                    detail, status_code=508)(scope, receive, send)
            return

        _current.set(
                replace(_current.get(), hop=hop))

        await self._app(scope, receive, send)


# unused
def guard(max_hop):

    def decorate(f):

        @functools.wraps(f)
        async def wrapper(agent_name, request):

            hop = _parse_hop(request.headers.get(HEADER))

            if hop >= max_hop:
                detail = f'gentleman: hop limit exceeded ({hop} >= {max_hop})' 
                raise HTTPException(status_code=508, detail=detail)

            _current.set(
                    replace(_current.get(), hop=hop))

            return await f(agent_name, request)

        return wrapper

    return decorate


def make_check(max_hop):

    async def check(request: Request):

        hop = _parse_hop(request.headers.get(HEADER))

        if hop >= max_hop:
            detail = f'gentleman: hop limit exceeded ({hop} >= {max_hop})' 
            raise HTTPException(status_code=508, detail=detail)

        _current.set(
                replace(_current.get(), hop=hop))

    return check


