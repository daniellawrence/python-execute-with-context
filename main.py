#!/usr/bin/env python
""" Execute a function with contenxt """
from pprint import pprint
import time

import jinja2


weights = {}
grade_limits = {}
function_tags = {}

DEFAULT_WEIGHT = 1
DEFAULT_MAX_GRADE = 'A+'
DEFUALT_DOC_STRING = ''


def weight(weight):

    def decorator(f):
        f_name = f.__name__
        weights[f_name] = weight
        return f
    return decorator


def tags(user_tags):

    def decorator(f):
        f_name = f.__name__
        if isinstance(user_tags, str):
            function_tags[f_name] = user_tags.split()
        else:
            function_tags[f_name] = user_tags
        return f
    return decorator


def max_grade_if_fail(weight):

    def decorator(f):
        grade_limits[f.__name__] = weight
        return f
    return decorator


def expand_dict(d):
    as_dict = {}
    for key, value in d.items():

        if isinstance(value, dict):
            as_dict[key] = expand_dict(value)
            continue

        if hasattr(value, 'to_dict'):
            as_dict[key] = expand_dict(value.to_dict)
            continue

        as_dict[key] = value
    return as_dict


class Context(object):

    R_KEYS = ['foo']

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value
        for r_key in self.R_KEYS:
            if r_key not in kwargs:
                assert NotImplemented(
                    'Missing required key "{}"'.format(r_key)
                )

    def __repr__(self):
        return "<Context {}>".format(id(self))

    @property
    def to_dict(self):
        return expand_dict(self.__dict__)


class ExecutionResult(object):

    def __init__(self, result, message):
        self.result = result
        self.message = message

    def __repr__(self):
        return "<ExecutionResult {}>".format(id(self))

    @property
    def to_dict(self):
        return expand_dict(self.__dict__)


@weight(10)
@max_grade_if_fail('A+')
@tags(['example'])
def plugin_function(ctx):
    """ Example execution function

    >{{meta.function.name}}< is awesome
    """
    return ExecutionResult(True, "plugin is a thing")


def plugin_info(plugin):
    """ static information about a plugin """
    f_name = plugin.__name__

    # metadata
    meta = {
        'function': {
            'name': f_name,
            'doc': plugin.__doc__ or '',
            'filename': plugin.__code__.co_filename
        },
        'weight': weights.get(f_name, DEFAULT_WEIGHT),
        'max_grade_if_fail': grade_limits.get(f_name, DEFAULT_WEIGHT),
        'tags':  function_tags.get(f_name, [])
    }

    return meta


def execute_plugin(plugin, ctx):
    # Execute the plugin, record the time it took to run.
    execute_start = time.time()
    result = plugin_function(ctx)
    execute_finish = time.time()

    # add a metadata set into the result set
    result.meta = plugin_info(plugin)
    raw_doc = result.meta.get('function', {}).get('doc', '')

    meta = {
        'ctx': ctx,
        'time': {
            'start': execute_start,
            'finish': execute_finish,
            'length': execute_finish - execute_start
        },
    }

    # apply generic plugin_info data into the meta data
    # that we have collected at run time.
    result.meta.update(meta)

    # render the doc_string via jinja2 templates
    data = result.to_dict
    doc_string_template = jinja2.Template(raw_doc)
    doc_string_rendered = doc_string_template.render(**data)
    result.meta['function']['doc_formatted'] = doc_string_rendered
    # return the results
    return result


def main():
    ctx = {
        'foo': 'bar'
    }
    ctx = Context(**ctx)
    results = execute_plugin(plugin_function, ctx)
    pprint(results.to_dict)


if __name__ == '__main__':
    main()
