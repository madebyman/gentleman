from fastapi import APIRouter, HTTPException, Request, Response

from ..._version import __version__


__all__ = ['create_health', 'create_health_router']


class _Health:

    def __init__(self, *gentlemen, include_in_schema=False):

        self._gentleman = gentlemen
        self._include_in_schema = include_in_schema

        # router
        self._router = self._build_router()

    @property
    def router(self):
        return self._router

    def _build_router(self):

        router = APIRouter()

        @router.api_route('/health',
                          methods=['GET', 'HEAD'],
                          include_in_schema=self._include_in_schema)

        async def health() -> dict[str, str]:
            return {'status': 'ok', 'version': __version__}

        @router.api_route('/ready',
                          methods=['GET', 'HEAD'],
                          include_in_schema=self._include_in_schema)

        async def ready(response: Response) -> dict:

            readiness = [v.readiness() for v in self._gentleman]

            ok = all(v.ready for v in readiness)

            if not ok:
                response.status_code = 503

            return {'status': 'ok' if ok else 'unready',
                    'instances': [v.model_dump(exclude_none=True)
                                  for v in readiness]}

        return router


def create_health(*gentlemen, include_in_schema=False):
    health = _Health(*gentlemen, include_in_schema=include_in_schema)
    return health


def create_health_router(*gentlemen, include_in_schema=False):
    router = _Health(*gentlemen, include_in_schema=include_in_schema).router
    return router


