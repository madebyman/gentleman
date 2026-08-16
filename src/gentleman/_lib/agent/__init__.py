from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .remote import RemoteAgent


__all__ = ['LocalAgent', 'RemoteAgent']


def __getattr__(name):

    if name == 'LocalAgent':
        from .local import LocalAgent

        globals()[name] = LocalAgent
        return LocalAgent

    if name == 'RemoteAgent':
        from .remote import RemoteAgent

        globals()[name] = RemoteAgent
        return RemoteAgent

    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def __dir__():
    return sorted(__all__)
