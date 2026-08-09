import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ._gentleman import create_gentleman

from ._lib.config import CorsSettings
from ._lib.loader import ConfigError

__all__ = ['create_app']

def create_app():

    try:
        gentleman = create_gentleman()

    except (ConfigError) as err:
        print(err, file=sys.stderr)
        sys.exit(1)

    if gentleman.is_bundled_example:
        print(f'gentleman: serving bundled example agents from '
              f'{gentleman.agents_dir}; '
              'mount or configure your own via GENTLEMAN_AGENTS_DIR',
              file=sys.stderr)

    app = FastAPI(
            title='gentleman', lifespan=gentleman.lifespan)

    app.add_middleware(
            CORSMiddleware, **CorsSettings().model_dump())

    return gentleman.attach(app)


