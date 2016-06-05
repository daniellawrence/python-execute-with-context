import os
import time

import jinja2

DEFAULT_WEIGHT = 1
DEFAULT_MAX_GRADE = 'A+'
DEFUALT_DOC_STRING = ''


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


class ExecutionResult(object):

    def __init__(self, result, message):
        self.result = result
        self.message = message

    def __repr__(self):
        return "<ExecutionResult {}>".format(id(self))

    def __str__(self):
        return "result={} message={}".format(self.result, self.message)

    @property
    def to_dict(self):
        return expand_dict(self.__dict__)


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


class CheckMaker(object):
    all_plugins = []
    weights = {}
    grade_limits = {}
    function_tags = {}
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
        return class_._instance

    def result(self, *args, **kwargs):
        r = ExecutionResult(*args, **kwargs)
        r.check = self
        return r

    def weight(self, weight):

        def decorator(f):
            f_name = f.__name__
            self.weights[f_name] = weight
            return f
        return decorator

    def tags(self, user_tags):

        def decorator(f):
            f_name = f.__name__
            if isinstance(user_tags, str):
                self.function_tags[f_name] = user_tags.split()
            else:
                self.function_tags[f_name] = user_tags
            return f
        return decorator

    def max_grade_if_fail(self, max_grade):

        def decorator(f):
            self.grade_limits[f.__name__] = max_grade
            return f
        return decorator

    def plugin_info(self, plugin):
        """ static information about a plugin """
        f_name = plugin.__name__

        # metadata
        meta = {
            'function': {
                'name': f_name,
                'doc': plugin.__doc__ or '',
                'filename': plugin.__code__.co_filename
            },
            'weight': self.weights.get(f_name, DEFAULT_WEIGHT),
            'max_grade_if_fail': self.grade_limits.get(f_name, DEFAULT_WEIGHT),
            'tags': self.function_tags.get(f_name, [])
        }
        return meta

    def load_plugins(self):

        for filename in os.listdir('plugins'):
            if filename.startswith('_'):
                continue
            if not filename.endswith('.py'):
                continue
            if '#' in filename:
                continue
            mod_name = filename[:-3]
            import_mod_name = 'plugins.{}'.format(mod_name)
            imported_mod = __import__(import_mod_name)
            mod = imported_mod.__dict__[mod_name]

            for check_fuction_name in dir(mod):
                if check_fuction_name.startswith('_'):
                    continue
                if not check_fuction_name.startswith('check_'):
                    continue

                check_function = mod.__dict__[check_fuction_name]
                self.all_plugins.append(check_function)

        return self.all_plugins

    def execute_plugin(self, plugin, ctx):
        # Execute the plugin, record the time it took to run.
        execute_start = time.time()
        result = plugin(ctx)
        execute_finish = time.time()

        # add a metadata set into the result set
        result.meta = self.plugin_info(plugin)
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
