__all__ = ['app', 'create_app']


def __getattr__(name):

    if name == 'create_app':
        from ._lib.app import create_app
        return create_app

    if name == 'app':
        from ._lib.app import create_app

        app = create_app()
        globals()['app'] = app

        return app

    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def __dir__():
    return sorted(__all__)
