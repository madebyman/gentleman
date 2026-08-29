import os
import sys
import json

from uuid import uuid4

import httpx

from ag_ui.core import RunAgentInput, UserMessage, AssistantMessage


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
                      timeout=httpx.Timeout(None, connect=10.0),
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


def _repl(url):

    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.formatted_text import HTML
        # from prompt_toolkit.history import FileHistory

        from rich.live import Live
        from rich.console import Console
        from rich.markdown import Markdown

    except (ImportError):
        print('interactive chat requires extras: '
              'pip install "gentleman-agents[chat]"', file=sys.stderr)
        sys.exit(1)

    thread_id = str(uuid4())
    history = []

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

                for v in _stream_server(url, thread_id, history):
                    chunks.append(v)
                    live.update(Markdown(''.join(chunks)))

        except (KeyboardInterrupt):
            history.pop()
            console.print('[yellow]Interrupted.[/yellow]')
            continue

        except (httpx.HTTPError, RuntimeError) as err:
            history.pop()
            console.print(f'[red]I do apologize — {err}[/red]')
            continue

        history.append(AssistantMessage(id=str(uuid4()),
                                        role='assistant',
                                        content=''.join(chunks)))


def _batch(url, prompt):

    thread_id = str(uuid4())
    history = [UserMessage(id=str(uuid4()), role='user', content=prompt)]

    stdout = sys.stdout
    last = ''

    try:
        for v in _stream_server(url, thread_id, history):
            if not v:
                continue

            stdout.write(v)
            stdout.flush()
            last = v

    except (httpx.HTTPError, RuntimeError) as err:
        if last:
            stdout.write('\n')
            stdout.flush()

        print(f'gentleman: {err}', file=sys.stderr)
        sys.exit(1)

    except (KeyboardInterrupt):
        print('gentleman: interrupted', file=sys.stderr)
        sys.exit(130)

    except (BrokenPipeError):
        os.dup2(os.open(os.devnull, os.O_WRONLY), stdout.fileno())
        sys.exit(141)

    if not last:
        print('gentleman: empty response', file=sys.stderr)
        sys.exit(1)

    if not last.endswith('\n'):
        stdout.write('\n')

    stdout.flush()


def chat(name_or_url, *args, **kwargs):

    url = _resolve_url(name_or_url)

    # repl
    if sys.stdin is not None and sys.stdin.isatty():
        return _repl(url)

    # batch
    raw = sys.stdin.buffer.read() if sys.stdin is not None else b''
    prompt = raw.decode('utf-8', errors='replace').strip()

    if not prompt:
        print('gentleman: no input on stdin', file=sys.stderr)
        sys.exit(1) 

    return _batch(url, prompt)


