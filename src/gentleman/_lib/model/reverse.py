from pydantic_ai.messages import ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.function import FunctionModel


REVERSE_MODEL = 'gentleman:reverse'
_chunk = 8


def _reply(messages):

    for v1 in reversed(messages):
        for v2 in reversed(v1.parts):

            if isinstance(v2, UserPromptPart):
                text = (v2.content if isinstance(v2.content, str) else
                        ' '.join(v3 for v3 in v2.content if isinstance(v3, str)))

                return text[::-1]

    return ''


def _reverse(messages, info):
    return ModelResponse(parts=[TextPart(_reply(messages))])


async def _reverse_stream(messages, info):

    text = _reply(messages)

    for i in range(0, len(text), _chunk):
        yield text[i:i + _chunk]


def make_reverse_model():
    return FunctionModel(
            _reverse, stream_function=_reverse_stream, model_name=REVERSE_MODEL)
