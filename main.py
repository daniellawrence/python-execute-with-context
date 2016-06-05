#!/usr/bin/env python
""" Execute a function with contenxt """
from pprint import pprint
from utils import CheckMaker, Context, score_to_grade

check = CheckMaker()

if __name__ == '__main__':
    check.load_plugins()
    print "found {} plugins".format(len(check.all_plugins))

    ctx = {
        'foo': 'bar'
    }
    ctx = Context(**ctx)

    all_results = []

    for p in check.all_plugins:
        info = check.plugin_info(p)
        r = check.execute_plugin(p, ctx)
        all_results.append(r)
        print "{:<20} {:<30} {:.5f}ms".format(
            info.get('function', {}).get('name'), r,
            r.meta.get('time').get('length')
        )

        pprint(r.to_dict)
        print
        print "-" * 70
        print

    max_score = 100
    possible_score = 0
    current_score = 0
    adjusted_score = 0

    for r in all_results:
        if max_score > r.score_limit:
            max_score = r.score_limit

        possible_score += r.weight
        current_score += r.score
        weighted_score = int((float(current_score) / possible_score) * 100)
        print r, r.score, r.weight, current_score, possible_score, \
            weighted_score

    adjusted_score = weighted_score
    if weighted_score > max_score:
        adjusted_score = max_score

    print possible_score
    print current_score
    print "%", weighted_score
    print "%", adjusted_score
    print "%", max_score

    grade = score_to_grade(adjusted_score)
    print '!', grade
