import json
from uuid import uuid4

import httpx

from ag_ui.core import RunAgentInput, UserMessage, AssistantMessage

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory

from rich.live import Live
from rich.console import Console
from rich.markdown import Markdown

def _resolve_url(name_or_url):

    if name_or_url.startswith(('http://', 'https://')):
        return name_or_url

    return f'http://localhost:8000/agents/{name_or_url.strip("/")}'


def _stream_server(url, thread_id, history):

    payload = RunAgentInput(thread_id=thread_id,
                            run_id=str(uuid4()),
                            messages=history,
                            tools=[],
                            context=[],
                            state=None,
                            forwarded_props=None,
    ).model_dump(by_alias=True)

    with httpx.stream('POST',
                      url,
                      json=payload,
                      timeout=None,
                      follow_redirects=True,
                      headers={'Accept': 'text/event-stream'}) as response:

        if response.status_code >= 400:
            response.read()

            raise RuntimeError(f'{response.status_code}: {response.text}')

        for v in response.iter_lines():

            if not v.startswith('data:'):
                continue

            event = json.loads(v[len('data:'):])

            if event['type'] == 'TEXT_MESSAGE_CONTENT':
                yield event['delta']

            elif event['type'] == 'RUN_ERROR':
                raise RuntimeError(event.get('message', 'agent run failed'))


def chat(name_or_url, *args, **kwargs):

    thread_id = str(uuid4())
    history = []

    endpoint = _resolve_url(name_or_url)

    session = PromptSession(
            HTML('<b>gentleman</b> <ansibrightblack>❯</ansibrightblack> '))

    console = Console()

    print('Hello! At your service. (Ctrl-D to exit)')

    while True:

        try:
            text = session.prompt()

        except (EOFError, KeyboardInterrupt):
            print('See you! It was a pleasure.')
            break

        if not text.strip():
            continue

        history.append(UserMessage(id=str(uuid4()), role='user', content=text))

        chunks = []

        try:
            with Live('',
                      console=console,
                      refresh_per_second=10,
                      vertical_overflow='visible') as live:

                for v in _stream_server(endpoint, thread_id, history):
                    chunks.append(v)
                    live.update(Markdown(''.join(chunks)))

        except (httpx.HTTPError, RuntimeError) as err:
            history.pop()
            console.print(f'[red]I do apologize — {err}[/red]')
            continue

        history.append(AssistantMessage(id=str(uuid4()),
                                        role='assistant',
                                        content=''.join(chunks)))


