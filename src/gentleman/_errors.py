class Error(RuntimeError):
    pass


class LoadError(Error):
    pass


class BuildError(Error):
    pass


class LifecycleError(Error):
    pass


class RemoteLoopError(Error):
    pass


class RemoteEmptyError(Error):
    pass


class RemoteTaskError(Error):
    pass



__all__ = [k for k, v in globals().items()
           if isinstance(v, type) and issubclass(v, Error)]
