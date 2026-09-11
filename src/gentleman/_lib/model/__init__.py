from .echo import ECHO_MODEL, make_echo_model


BUILTIN_PREFIX = 'gentleman:'
BUILTIN_MODELS = {ECHO_MODEL: make_echo_model}


def resolve_model(name):
    factory = BUILTIN_MODELS.get(name)
    return factory() if factory is not None else name

