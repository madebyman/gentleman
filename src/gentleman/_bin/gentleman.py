import argparse
import shutil
import sys

from pathlib import Path
from string import Template

from importlib.metadata import version
from importlib.resources import files, as_file

import uvicorn

def init(dest_dir, *args, **kwargs):

    # src
    src_dir_path = files('gentleman') / '_tmpl'

    # dest
    dest_dir_path = Path(dest_dir).expanduser().resolve()

    try:
         dest_dir_path.mkdir(parents=True, exist_ok=True)

    except (FileExistsError) as err:
        print(err, file=sys.stderr)
        sys.exit(1)

    # context and overwrite files
    context = {'project_name': dest_dir_path.name,
                'gentleman_version': version('gentleman')}

    overwrite_target_files = ['pyproject.toml', 'README.md']

    # copy
    with as_file(src_dir_path) as p:

        for v in p.iterdir():

            dest_file_path = dest_dir_path / v.name

            if v.is_dir():
                shutil.copytree(v, dest_file_path, dirs_exist_ok=True)
                continue

            if dest_file_path.exists() or not v.is_file():
                continue

            if v.name in overwrite_target_files:
                dest_file_path.write_text(
                    Template(v.read_text()).substitute(context))

            else:
                shutil.copy2(v, dest_file_path)

    print(f'Initialized project `{dest_dir_path.name}` at `{dest_dir_path}`')


def dev(*args, **kwargs):
    uvicorn.run(
            'gentleman:app', host='127.0.0.1', port=8000, reload=True)


def run(*args, **kwargs):
    uvicorn.run(
            'gentleman:app', host='0.0.0.0', port=8000)


# extra [chat]
def chat(*args, **kwargs):

    try:
        from .gentleman_chat import chat

    except (ImportError):
        print('chat command requires extras: '
              'pip install "gentleman[chat]"', file=sys.stderr)

        sys.exit(1)

    chat(*args, **kwargs)


def main():

    commands = {
        'dev': {'cmd': dev , 'args': None},
        'run': {'cmd': run , 'args': None},

        'init': {'cmd': init, 'args': ['dir', {'nargs': '?', 'default': '.'}]},
        'chat': {'cmd': chat, 'args': ['url', {}]},
    }

    # parser
    parser = argparse.ArgumentParser(
            prog='gentleman', description='gentleman cli')

    sub = parser.add_subparsers(dest='cmd', required=True)

    for k, v in commands.items():
        parser_command = sub.add_parser(k)

        if v['args'] is None:
            continue

        arg_name, arg_option = v['args'] 
        parser_command.add_argument(arg_name, **arg_option)

    args = parser.parse_args()

    command = commands[args.cmd]

    command['cmd'](getattr(args, command['args'][0]) 
            if command['args'] else None)


