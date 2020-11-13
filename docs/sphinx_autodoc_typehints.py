import inspect
import sys
import textwrap
import typing
from typing import get_type_hints, TypeVar, Any, AnyStr, Generic, Union

from sphinx.util import logging
from sphinx.util.inspect import signature as Signature, stringify_signature

import type_globals

try:
    from typing_extensions import Protocol
except ImportError:
    Protocol = None

logger = logging.getLogger(__name__)
pydata_annotations = {'Any', 'AnyStr', 'Callable', 'ClassVar', 'NoReturn', 'Optional', 'Tuple',
                      'Union'}


def format_annotation(annotation, fully_qualified=False):
    if inspect.isclass(annotation) and annotation.__module__ == 'builtins':
        if annotation.__qualname__ == 'NoneType':
            return '``None``'
        else:
            return ':py:class:`{}`'.format(annotation.__qualname__)

    annotation_cls = annotation if inspect.isclass(annotation) else type(annotation)
    if annotation_cls.__module__ == 'typing':
        class_name = str(annotation).split('[')[0].split('.')[-1]
        params = None
        module = 'typing'
        extra = ''

        origin = getattr(annotation, '__origin__', None)
        if inspect.isclass(origin):
            annotation_cls = annotation.__origin__
            try:
                mro = annotation_cls.mro()
                if Generic in mro or (Protocol and Protocol in mro):
                    module = annotation_cls.__module__
            except TypeError:
                pass  # annotation_cls was either the "type" object or typing.Type

        if annotation is Any:
            return ':py:data:`{}typing.Any`'.format("" if fully_qualified else "~")
        elif annotation is AnyStr:
            return ':py:data:`{}typing.AnyStr`'.format("" if fully_qualified else "~")
        elif isinstance(annotation, TypeVar):
            bound = annotation.__bound__
            if bound:
                if 'ForwardRef(' in str(bound):
                    try:
                        bound = bound._evaluate(sys.modules[annotation.__module__].__dict__, None)
                    except:
                        try:
                            bound = bound._evaluate(type_globals.__dict__, None)
                        except:
                            bound = bound.__forward_arg__
                return format_annotation(bound, fully_qualified)
            return '\\%r' % annotation
        elif (annotation is Union or getattr(annotation, '__origin__', None) is Union or
              hasattr(annotation, '__union_params__')):
            if hasattr(annotation, '__union_params__'):
                params = annotation.__union_params__
            elif hasattr(annotation, '__args__'):
                params = annotation.__args__

            if params and len(params) == 2 and (hasattr(params[1], '__qualname__') and
                                                params[1].__qualname__ == 'NoneType'):
                class_name = 'Optional'
                params = (params[0],)
        elif annotation_cls.__qualname__ == 'Tuple' and hasattr(annotation, '__tuple_params__'):
            params = annotation.__tuple_params__
            if annotation.__tuple_use_ellipsis__:
                params += (Ellipsis,)
        elif annotation_cls.__qualname__ == 'Callable':
            arg_annotations = result_annotation = None
            if hasattr(annotation, '__result__'):
                arg_annotations = annotation.__args__
                result_annotation = annotation.__result__
            elif getattr(annotation, '__args__', None):
                arg_annotations = annotation.__args__[:-1]
                result_annotation = annotation.__args__[-1]

            if arg_annotations in (Ellipsis, (Ellipsis,)):
                params = [Ellipsis, result_annotation]
            elif arg_annotations is not None:
                params = [
                    '\\[{}]'.format(
                        ', '.join(
                            format_annotation(param, fully_qualified)
                            for param in arg_annotations)),
                    result_annotation
                ]
        elif str(annotation).startswith('typing.ClassVar[') and hasattr(annotation, '__type__'):
            # < py3.7
            params = (annotation.__type__,)
        elif hasattr(annotation, 'type_var'):
            # Type alias
            class_name = annotation.name
            params = (annotation.type_var,)
        elif getattr(annotation, '__args__', None) is not None:
            params = annotation.__args__
        elif hasattr(annotation, '__parameters__'):
            params = annotation.__parameters__

        if params:
            extra = '\\[{}]'.format(', '.join(
                format_annotation(param, fully_qualified) for param in params))

        return '{prefix}`{qualify}{module}.{name}`{extra}'.format(
            prefix=':py:data:' if class_name in pydata_annotations else ':py:class:',
            qualify="" if fully_qualified else "~",
            module=module,
            name=class_name,
            extra=extra
        )
    elif annotation is Ellipsis:
        return '...'
    elif (inspect.isfunction(annotation) and annotation.__module__ == 'typing' and
          hasattr(annotation, '__name__') and hasattr(annotation, '__supertype__')):
        return ':py:func:`{qualify}typing.NewType`\\(:py:data:`~{name}`, {extra})'.format(
            qualify="" if fully_qualified else "~",
            name=annotation.__name__,
            extra=format_annotation(annotation.__supertype__, fully_qualified),
        )
    elif inspect.isclass(annotation) or inspect.isclass(getattr(annotation, '__origin__', None)):
        if not inspect.isclass(annotation):
            annotation_cls = annotation.__origin__

        extra = ''
        try:
            mro = annotation_cls.mro()
        except TypeError:
            pass
        else:
            if Generic in mro or (Protocol and Protocol in mro):
                params = (getattr(annotation, '__parameters__', None) or
                          getattr(annotation, '__args__', None))
                if params:
                    extra = '\\[{}]'.format(', '.join(
                        format_annotation(param, fully_qualified) for param in params))

        return ':py:class:`{qualify}{module}.{name}`{extra}'.format(
            qualify="" if fully_qualified else "~",
            module=annotation.__module__,
            name=annotation_cls.__qualname__,
            extra=extra
        )

    return str(annotation)


def process_signature(app, what: str, name: str, obj, options, signature, return_annotation):
    if not callable(obj):
        return

    if what in ('class', 'exception'):
        obj = getattr(obj, '__init__', getattr(obj, '__new__', None))

    if not getattr(obj, '__annotations__', None):
        return

    obj = inspect.unwrap(obj)
    signature = Signature(obj)
    parameters = [
        param.replace(annotation=inspect.Parameter.empty)
        for param in signature.parameters.values()
    ]

    if '<locals>' in obj.__qualname__:
        logger.warning(
            'Cannot treat a function defined as a local function: "%s"  (use @functools.wraps)',
            name)
        return

    if parameters:
        if what in ('class', 'exception'):
            del parameters[0]
        elif what == 'method':
            outer = inspect.getmodule(obj)
            for clsname in obj.__qualname__.split('.')[:-1]:
                outer = getattr(outer, clsname)

            method_name = obj.__name__
            if method_name.startswith("__") and not method_name.endswith("__"):
                # If the method starts with double underscore (dunder)
                # Python applies mangling so we need to prepend the class name.
                # This doesn't happen if it always ends with double underscore.
                class_name = obj.__qualname__.split('.')[-2]
                method_name = "_{c}{m}".format(c=class_name, m=method_name)

            method_object = outer.__dict__[method_name] if outer else obj
            if not isinstance(method_object, (classmethod, staticmethod)):
                del parameters[0]

    signature = signature.replace(
        parameters=parameters,
        return_annotation=inspect.Signature.empty)

    return stringify_signature(signature).replace('\\', '\\\\'), None


def get_all_type_hints(obj, name):
    rv = {}

    try:
        rv = get_type_hints(obj)
    except (AttributeError, TypeError, RecursionError):
        # Introspecting a slot wrapper will raise TypeError, and and some recursive type
        # definitions will cause a RecursionError (https://github.com/python/typing/issues/574).
        pass
    except NameError as exc:
        try:
            rv = get_type_hints(obj, localns=type_globals.__dict__)
        except Exception as exc:
            logger.warning('Cannot resolve forward reference in type annotations of "%s": %s',
                           name, exc)
            rv = obj.__annotations__

    if rv:
        return rv

    rv = backfill_type_hints(obj, name)

    try:
        obj.__annotations__ = rv
    except (AttributeError, TypeError):
        return rv

    try:
        rv = get_type_hints(obj)
    except (AttributeError, TypeError):
        pass
    except NameError as exc:
        try:
            rv = get_type_hints(obj, localns=type_globals.__dict__)
        except:
            logger.warning('Cannot resolve forward reference in type annotations of "%s": %s',
                           name, exc)
            rv = obj.__annotations__

    return rv


def backfill_type_hints(obj, name):
    parse_kwargs = {}
    if sys.version_info < (3, 8):
        try:
            import typed_ast.ast3 as ast
        except ImportError:
            return {}
    else:
        import ast
        parse_kwargs = {'type_comments': True}

    def _one_child(module):
        children = module.body  # use the body to ignore type comments

        if len(children) != 1:
            logger.warning(
                'Did not get exactly one node from AST for "%s", got %s', name, len(children))
            return

        return children[0]

    try:
        obj_ast = ast.parse(textwrap.dedent(inspect.getsource(obj)), **parse_kwargs)
    except TypeError:
        return {}

    obj_ast = _one_child(obj_ast)
    if obj_ast is None:
        return {}

    try:
        type_comment = obj_ast.type_comment
    except AttributeError:
        return {}

    if not type_comment:
        return {}

    try:
        comment_args_str, comment_returns = type_comment.split(' -> ')
    except ValueError:
        logger.warning('Unparseable type hint comment for "%s": Expected to contain ` -> `', name)
        return {}

    rv = {}
    if comment_returns:
        rv['return'] = comment_returns

    args = load_args(obj_ast)
    comment_args = split_type_comment_args(comment_args_str)
    is_inline = len(comment_args) == 1 and comment_args[0] == "..."
    if not is_inline:
        if args and args[0].arg in ("self", "cls") and len(comment_args) != len(args):
            comment_args.insert(0, None)  # self/cls may be omitted in type comments, insert blank

        if len(args) != len(comment_args):
            logger.warning('Not enough type comments found on "%s"', name)
            return rv

    for at, arg in enumerate(args):
        arg_key = getattr(arg, "arg", None)
        if arg_key is None:
            continue

        if is_inline:  # the type information now is tied to the argument
            value = getattr(arg, "type_comment", None)
        else:  # type data from comment
            value = comment_args[at]

        if value is not None:
            rv[arg_key] = value

    return rv


def load_args(obj_ast):
    func_args = obj_ast.args
    args = []
    pos_only = getattr(func_args, 'posonlyargs', None)
    if pos_only:
        args.extend(pos_only)

    args.extend(func_args.args)
    if func_args.vararg:
        args.append(func_args.vararg)

    args.extend(func_args.kwonlyargs)
    if func_args.kwarg:
        args.append(func_args.kwarg)

    return args


def split_type_comment_args(comment):
    def add(val):
        result.append(val.strip().lstrip("*"))  # remove spaces, and var/kw arg marker

    comment = comment.strip().lstrip("(").rstrip(")")
    result = []
    if not comment:
        return result

    brackets, start_arg_at, at = 0, 0, 0
    for at, char in enumerate(comment):
        if char in ("[", "("):
            brackets += 1
        elif char in ("]", ")"):
            brackets -= 1
        elif char == "," and brackets == 0:
            add(comment[start_arg_at:at])
            start_arg_at = at + 1

    add(comment[start_arg_at: at + 1])
    return result


def process_docstring(app, what, name, obj, options, lines):
    if isinstance(obj, property):
        obj = obj.fget

    if callable(obj):
        if what in ('class', 'exception'):
            obj = getattr(obj, '__init__')

        obj = inspect.unwrap(obj)
        type_hints = get_all_type_hints(obj, name)

        for argname, annotation in type_hints.items():
            if argname == 'return':
                continue  # this is handled separately later
            if argname.endswith('_'):
                argname = '{}\\_'.format(argname[:-1])

            formatted_annotation = format_annotation(
                annotation, fully_qualified=app.config.typehints_fully_qualified)

            searchfor = ':param {}:'.format(argname)
            insert_index = None

            for i, line in enumerate(lines):
                if line.startswith(searchfor):
                    insert_index = i
                    break

            if insert_index is None and app.config.always_document_param_types:
                lines.append(searchfor)
                insert_index = len(lines)

            if insert_index is not None:
                lines.insert(
                    insert_index,
                    ':type {}: {}'.format(argname, formatted_annotation)
                )

        if 'return' in type_hints and what not in ('class', 'exception'):
            formatted_annotation = format_annotation(
                type_hints['return'], fully_qualified=app.config.typehints_fully_qualified)

            insert_index = len(lines)
            for i, line in enumerate(lines):
                if line.startswith(':rtype:'):
                    insert_index = None
                    break
                elif line.startswith(':return:') or line.startswith(':returns:'):
                    insert_index = i

            if insert_index is not None:
                if insert_index == len(lines):
                    # Ensure that :rtype: doesn't get joined with a paragraph of text, which
                    # prevents it being interpreted.
                    lines.append('')
                    insert_index += 1

                lines.insert(insert_index, ':rtype: {}'.format(formatted_annotation))


def builder_ready(app):
    if app.config.set_type_checking_flag:
        typing.TYPE_CHECKING = True


def setup(app):
    app.add_config_value('set_type_checking_flag', False, 'html')
    app.add_config_value('always_document_param_types', False, 'html')
    app.add_config_value('typehints_fully_qualified', False, 'env')
    app.connect('builder-inited', builder_ready)
    app.connect('autodoc-process-signature', process_signature)
    app.connect('autodoc-process-docstring', process_docstring)
    return dict(parallel_read_safe=True)
