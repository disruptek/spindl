import logging

log = logging.getLogger(__name__)
logformat = '%(levelname)s\t%(asctime)s.%(msecs)d\t%(module)s/%(funcName)s: %(message)s'


def setup(default, format=logformat, **kw):
    logging.basicConfig(level=default.upper(), format=format, datefmt='%H:%M:%S')
    modules = ['requests', 'gevent']
    levels = dict([(m, 'WARN') for m in modules])
    levels.update(kw)
    # hack to elide default from kwargs
    for name, level in [x for x in levels.items() if x[0]]:
        logging.getLogger(name).setLevel(level.upper())
