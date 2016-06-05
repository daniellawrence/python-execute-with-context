#!/usr/bin/env python
""" Execute a function with contenxt """
from pprint import pprint
from utils import CheckMaker, Context, score_to_grade, CheckGroup

check = CheckMaker()

if __name__ == '__main__':
    check.load_plugins()
    print "found {} plugins".format(len(check.all_plugins))
    group = CheckGroup(check)
    group.execute_checks()

    score = group.calculate_score()
    grade = group.calculate_grade()

    print "score:", score
    print "group:", grade
