import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ._gentleman import create_gentleman
from ._errors import BuildError, LoadError

from ._lib.settings import CorsSettings


__all__ = ['create_app']


def create_app():

    try:
        gentleman = create_gentleman()

    except (LoadError, BuildError) as err:
        print(err, file=sys.stderr)
        sys.exit(1)

    if gentleman.is_bundled_example:
        print(f'gentleman: serving bundled example agents from '
              f'{gentleman.agents_dir}; '
              'mount or configure your own via GENTLEMAN_APP_AGENTS_DIR',
              file=sys.stderr)

    app = FastAPI(
            title=gentleman.app_name, lifespan=gentleman.lifespan)

    app.add_middleware(
            CORSMiddleware, **CorsSettings().model_dump())

    return gentleman.attach(app)


