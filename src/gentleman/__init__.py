from ._errors import LoadError, BuildError


__all__ = ['app', 'create_app', 'create_gentleman', 'LoadError', 'BuildError']


def __getattr__(name):

    if name == 'app':
        from ._app import create_app

        try:
            app = create_app()

        except (AttributeError) as err:
            raise RuntimeError(
                    f'gentleman: failed to create app: {err}') from err

        globals()['app'] = app

        return app

    if name == 'create_app':
        from ._app import create_app
        return create_app

    if name == 'create_gentleman':
        from ._gentleman import create_gentleman
        return create_gentleman

    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def __dir__():
    return sorted(__all__)
