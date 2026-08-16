class Error(RuntimeError):
    pass


class LoadError(Error):
    pass


class BuildError(Error):
    pass


class LifecycleError(Error):
    pass

