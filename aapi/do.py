import argparse
import inspect
import io
import logging
import re
import sys
import types
import os
import traceback

from aapi import (
    ApiParser,
    Har2Template,
    Har2Postman,
    PostmanCreator
)

COMMAND_ARGS_TAG = 'cc_'


class PositionalArg(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        namespace.positional.append(values)


def get_common_arguments():
    group = argparse.ArgumentParser('Common', add_help=False)
    group.add_argument('-v', '--verbose', action='store_true', help='Enable logging')
    return group


def _doc_to_args(doc):
    """Converts a docstring documenting arguments into a dict."""
    m = None
    offset = None
    in_arg = False
    out = {}
    for l in doc.splitlines():
        if l.strip() == 'Args:':
            in_arg = True
        elif in_arg:
            if not l.strip():
                break
            if offset is None:
                offset = len(l) - len(l.lstrip())
            l = l[offset:]
            if l[0] == ' ' and m:
                out[m.group(1)] += ' ' + l.lstrip()
            else:
                m = re.match(r'^([a-z_]+): (.+)$', l.strip())
                out[m.group(1)] = m.group(2)
    return out


def make_subparser(subparsers, parents, method, arguments=None):
    """Returns an argparse subparser to create a 'subcommand' to adb."""
    name = method.__name__.lower()
    help = method.__doc__.splitlines()[0]
    subparser = subparsers.add_parser(
        name=name, description=help, help=help.rstrip('.'), parents=parents)
    subparser.set_defaults(method=method, positional=[])
    argspec = inspect.getfullargspec(method)

    # Figure out positionals and default argument, if any. Explicitly includes
    # arguments that default to '' but excludes arguments that default to None.
    offset = len(argspec.args) - len(argspec.defaults or [])
    positional = []
    for i in range(0, len(argspec.args)):
        if i > offset and argspec.defaults[i - offset - 1] is None:
            break
        positional.append(argspec.args[i])
    defaults = [None] * offset + list(argspec.defaults or [])

    # Add all arguments so they append to args.positional.
    args_help = _doc_to_args(method.__doc__)
    for name, default in zip(positional, defaults):
        if not isinstance(default, (None.__class__, str)):
            continue
        subparser.add_argument(
            '-{}'.format(name), '--{}'.format(name),
            help=(arguments or {}).get(name, args_help.get(name)),
            default=default, nargs='?' if default is not None else None,
            dest='{flag}{arg_name}'.format(flag=COMMAND_ARGS_TAG, arg_name=name))
    if argspec.varargs:
        subparser.add_argument(
            argspec.varargs, nargs=argparse.REMAINDER,
            help=(arguments or {}).get(argspec.varargs, args_help.get(argspec.varargs)))
    return subparser


def _run_method(args):
    """Runs a method registered via MakeSubparser."""
    # logging.info('%s(%s)', args.method.__name__, ', '.join(args.positional))
    xargs = {k.replace(COMMAND_ARGS_TAG, ''): v for k, v in args.__dict__.items()
             if k.startswith(COMMAND_ARGS_TAG)}
    result = args.method(**xargs)
    if result is not None:
        if isinstance(result, io.StringIO):
            sys.stdout.write(result.getvalue())
        elif isinstance(result, (list, types.GeneratorType)):
            r = ''
            for r in result:
                r = str(r)
                sys.stdout.write(r)
            if not r.endswith('\n'):
                sys.stdout.write('\n')
        else:
            result = str(result)
            sys.stdout.write(result)
            if not result.endswith('\n'):
                sys.stdout.write('\n')
    return 0


def start_cli(args):
    """Starts a common CLI interface for this usb path and protocol."""
    try:
        return _run_method(args)
    except Exception as e:  # pylint: disable=broad-except
        sys.stdout.write(str(e))
        traceback.print_exc()
        return 1


def case(to, d, n, ex):
    """Convert json file to postman or eolinker request case

    Args:
        to: {postman, eolinker} choice convert type
        d: json template files directory path
        n: group name
        ex: {openapi}
    """
    if to is None or to not in ['postman', 'eolinker']:
        logging.error('%s-%s', 'Convert Case', '-to option must be used and value choice from {postman, eolinker}')
        return 2

    if not os.path.exists(d):
        logging.error('%s-%s', 'Convert Case', '-d value json templates file dir not exists')
        return 3

    if not os.path.isdir(d):
        logging.error('%s-%s', 'Convert Case', '-d this path not directory')
        return 4

    group_name = os.path.basename(os.path.abspath(d)) if n is None else n
    if to == 'postman':
        parser = ApiParser(host='{{' + group_name + '}}', dir_url=d)
        creator = PostmanCreator(name=group_name, output_url='.')
        creator.create_apis(parser.create_request_cases())
        creator.create_apis(parser.create_request_cases())


def har(to, f):
    """Convert har file to postman or template json

    Args:
        to: {postman, template} choice convert type
        f: har file
    """
    if to is None or to not in ['postman', 'template']:
        logging.error('%s-%s', '.har to json', '-to option must be used and value choice from {postman, template}')
        return 2

    if not os.path.exists(f):
        logging.error('%s-%s', '.har to json', 'har file: {} was not exists'.format(f))
        return 4

    dir_name = f.replace('.har', '') if f.endswith('.har') else f

    if to == 'template':
        if not os.path.isdir(dir_name):
            os.makedirs(dir_name)
        parser = Har2Template(dir_path=dir_name, file_path=f)
        parser.create_json()
    elif to == 'postman':
        parser = Har2Postman(dir_path=dir_name, file_path=f, group_name=dir_name)
        parser.create_json()


def main():
    common = get_common_arguments()
    parents = [common]

    parser = argparse.ArgumentParser(
        description=sys.modules[__name__].__doc__, parents=[common])
    subparsers = parser.add_subparsers(title='Commands', dest='command_name')

    subparser = subparsers.add_parser(name='help', help='Prints the commands available')

    make_subparser(subparsers, parents, case)
    make_subparser(subparsers, parents, har)

    if len(sys.argv) == 1:
        parser.print_help()
        return 2

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Hacks so that the generated doc is nicer.
    if args.command_name == 'help':
        parser.print_help()
        return 0

    return start_cli(args)


if __name__ == '__main__':
    sys.exit(main())
