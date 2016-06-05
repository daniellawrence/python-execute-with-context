import operator
import os
import time

import jinja2

DEFAULT_WEIGHT = 1
DEFAULT_MAX_GRADE = 'A+'
DEFUALT_DOC_STRING = ''


score_map = {
    'A+': 97,
    'A': 93,
    'A-': 90,
    'B+': 87,
    'B': 83,
    'B-': 80,
    'C+': 77,
    'C': 73,
    'C-': 70,
    'D+': 67,
    'D': 63,
    'D-': 60,
    'F': 59
}


class CheckGroup(object):

    def __init__(self, checker):
        self.checker = checker
        self.checks = checker.all_plugins
        ctx_dict = {
            'foo': 'bar'
        }
        self.ctx = Context(**ctx_dict)
        self.results = []

    def execute_checks(self):
        for check in self.checks:
            r = self.checker.execute_plugin(check, self.ctx)
            print "{:<20} {:<30} {:.5f}ms".format(
                r.meta.get('function', {}).get('name'),
                r,
                r.meta.get('time').get('length')
            )

            self.results.append(r)
        return self.results

    def calculate_score(self):
        max_score = 100
        possible_score = 0
        current_score = 0
        adjusted_score = 0

        for r in self.results:
            if max_score > r.score_limit:
                max_score = r.score_limit

            possible_score += r.weight
            current_score += r.score
            weighted_score = int((float(current_score) / possible_score) * 100)

        adjusted_score = weighted_score
        if weighted_score > max_score:
            adjusted_score = max_score

        return adjusted_score

    def calculate_grade(self):
        score = self.calculate_score()
        grade = score_to_grade(score)
        return grade


def score_to_grade(lookup_score):

    for grade, score in sorted(score_map.items(), key=operator.itemgetter(1)):
        if lookup_score <= score:
            return grade
    return 'A+'


def max_score_from_max_grade(lookup_grade):
    if lookup_grade == 'F':
        return 60
    return score_map.get(lookup_grade, 97) + 3


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
        f_name = self.meta.get('function', {}).get('name')
        result = self.result
        if not f_name:
            f_name = id(self)

        return "<ExecutionResult {}:{}>".format(f_name, result)

    def __str__(self):
        return "result={} message={}".format(self.result, self.message)

    @property
    def score_limit(self):
        max_score = self.meta.get('max_score_if_fail', 100)
        return max_score

    @property
    def weight(self):
        return self.meta.get('weight', 1)

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
        max_grade_if_fail = self.grade_limits.get(f_name, DEFAULT_MAX_GRADE)
        max_score_if_fail = max_score_from_max_grade(max_grade_if_fail)
        weight = self.weights.get(f_name, DEFAULT_WEIGHT)

        # metadata
        meta = {
            'function': {
                'name': f_name,
                'doc': plugin.__doc__ or '',
                'filename': plugin.__code__.co_filename
            },
            'weight': weight,
            'max_grade_if_fail': max_grade_if_fail,
            'max_score_if_fail': max_score_if_fail,
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
        weight = result.meta.get('weight')

        meta = {
            'ctx': ctx,
            'time': {
                'start': execute_start,
                'finish': execute_finish,
                'length': execute_finish - execute_start
            },
        }

        result.score = 0
        if result.result is True:
            result.score = weight

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
