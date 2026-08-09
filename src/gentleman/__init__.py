__all__ = ['app', 'create_app', 'create_gentleman']

def __getattr__(name):

    if name == 'app':
        from ._app import create_app

        app = create_app()
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
