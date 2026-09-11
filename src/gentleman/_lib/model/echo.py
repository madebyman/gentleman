from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel


ECHO_MODEL = 'gentleman:echo'
_chunk = 8


def _reply(messages):

    for v1 in reversed(messages):
        for v2 in reversed(v1.parts):

            if isinstance(v2, UserPromptPart):
                text = (v2.content if isinstance(v2.content, str) else
                        ' '.join(v3 for v3 in v2.content if isinstance(v3, str)))

                return f'[echo] {text}'

    return '[echo]'


def _echo(messages, info):
    return ModelResponse(parts=[TextPart(_reply(messages))])


async def _echo_stream(messages, info):

    text = _reply(messages)

    for i in range(0, len(text), _chunk):
        yield text[i:i + _chunk]


def make_echo_model():
    return FunctionModel(
            _echo, stream_function=_echo_stream, model_name=ECHO_MODEL)

