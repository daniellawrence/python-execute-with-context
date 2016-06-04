#!/usr/bin/env python
""" Execute a function with contenxt """
from utils import CheckMaker, Context

check = CheckMaker()

if __name__ == '__main__':
    check.load_plugins()
    print "found {} plugins".format(len(check.all_plugins))

    ctx = {
        'foo': 'bar'
    }
    ctx = Context(**ctx)

    for p in check.all_plugins:
        info = check.plugin_info(p)
        r = check.execute_plugin(p, ctx)
        print "{:<20} {:<30} {:.5f}ms".format(
            info.get('function', {}).get('name'), r,
            r.meta.get('time').get('length')
        )
