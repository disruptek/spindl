#!/usr/bin/env python
"""
SPINDL3.

(c) 2014 Andy Davidoff

"""
import sys
import os
import logging
import os.path
import stat
from subprocess import check_output, CalledProcessError
from gevent.pool import Group
from gevent.queue import JoinableQueue
from gevent import monkey, Greenlet, spawn
import logger

# FIXME: move this to JSON
FILETYPE_SNIFFER = {
    'RIFF (little-endian) data, WAVE audio':    'wave',
    'FLAC audio bitstream data':                'flac',
    'MPEG v4 system, iTunes AAC-LC':            'alac',
    'AIFF-C compressed audio':                  'aiff',
    'AIFF audio':                               'aiff',
}

# gevent patching
monkey.patch_all(thread=False, select=False)

log = logging.getLogger(__name__)


class BadMusicFile(Exception):
    def __str__(self):
        return self.message


class MusicFile(object):
    """An input file from the user"""
    def __init__(self, filename):
        self.filename = filename
        self.basename = os.path.basename(filename)
        self.stat = None

    def __str__(self):
        return self.filename

    def __repr__(self):
        return '<MF:{}>'.format(self.basename)

    def is_regular_file(self):
        try:
            self.stat = os.stat(self.filename)
            if stat.S_ISREG(self.stat.st_mode):
                return True
        # FIXME: non-existent files qualify as irregular
        except OSError, e:
            pass
        return False

    def sniff_filetype(self, filename):
        try:
            # FIXME: use something more x-platform?
            cmd = ['file', '-b', filename]
            output = check_output(cmd, stdin=None, stderr=None)
        except CalledProcessError, e:
            log.error(str(e))
            return None
        for search, name in FILETYPE_SNIFFER.items():
            if search in output:
                return name
        return None

    def should_ignore(self):
        filetype = self.sniff_filetype(self.filename)
        if filetype is None:
            # FIXME: probably want a special handler for this
            log.info("unable to sniff filetype of {}".format(self))
            return True
        return False


class FileQueue(JoinableQueue):
    """Where files go to die"""
    def put(self, fn, *args, **kw):
        if isinstance(fn, MusicFile):
            mf = fn
        elif isinstance(fn, basestring):
            try:
                mf = MusicFile(fn.strip())
            except BadMusicFile, e:
                log.error(str(e))
                return
        else:
            raise NotImplementedError("bad input: {!r}".format(fn))
        log.debug("adding {} to queue".format(mf))
        return JoinableQueue.put(self, mf, *args, **kw)

    def put_iterable(self, iterable):
        for n in iterable:
            try:
                mf = MusicFile(n.strip())
            except BadMusicFile, e:
                log.error(str(e))
                continue
            if not mf.is_regular_file():
                log.info("skipping {}".format(mf))
                continue
            self.put(mf)

    def get(self, *args, **kw):
        result = JoinableQueue.get(self, *args, **kw)
        log.debug("operating on {}".format(result))
        return result


class WorkerPool(Group):
    """Unbounded collection of Worker greenlets"""


class Worker(Greenlet):
    """Coroutine for processing files from FileQueue"""
    def __init__(self, queue, *args, **kw):
        self.queue = queue
        Greenlet.__init__(self, *args, **kw)

    def _run(self): # noqa
        while self.queue.qsize():
            mf = self.queue.get()
            try:
                if mf.should_ignore():
                    continue
                log.debug("would work on {!r}".format(mf))
            except Exception, e:
                log.error("error: {!s}".format(e))
            finally:
                self.queue.task_done()


def main(workers=2, **args):

    queue = FileQueue()
    pool = WorkerPool()

    try:
        for _ in range(workers):
            green = Worker(queue)
            pool.start(green)

        queue.put_iterable(args['files'])
        if not sys.stdin.isatty():
            queue.put_iterable(sys.stdin.readlines())

        if queue.qsize():
            queue.join()
        pool.join()
    except KeyboardInterrupt:
        pool.kill()
        exit(1)


if __name__ == "__main__":
    import argparse
    from setproctitle import setproctitle

    title = os.path.basename(os.path.abspath(sys.argv[0])).split('.')[0]
    setproctitle(title)

    parser = argparse.ArgumentParser(description="{} - all your disc are belong to us".format(title),
                                     epilog="(psst. you can pass source filenames on stdin as well)",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     fromfile_prefix_chars='@')
    parser.add_argument('--temp', type=str, default='/Volumes/RAM Disk/',
                        help='temporary filesystem')
    parser.add_argument('--no-s3', action='store_true', default=True,
                        help='do not modify S3 objects')
    parser.add_argument('--no-fs', action='store_true', default=True,
                        help='do not modify source files')
    parser.add_argument('--workers', type=int, default=2, metavar='#',
                        help='sorta like threads')
    parser.add_argument('--debug', type=str, default='DEBUG', metavar='LEVEL',
                        help='debug level or module1=level,module2=level')
    parser.add_argument('files', nargs='*', metavar='FILE',
                        help='filenames to process')

    if 'xterm' in os.environ.get('TERM', ''):
        print "\033]2;{}\007".format(title)

    def debug_level(option):
        if '=' in option:
            return option.split('=')
        if option.upper() in ('DEBUG', 'INFO', 'WARN', 'ERROR'):
            return ('', option)
        return (option, 'DEBUG')

    cliargs = parser.parse_args()
    debuglevels = dict([debug_level(level) for level in cliargs.debug.split(',')])
    logger.setup(debuglevels.get('', 'WARN'), **debuglevels)

    main(**cliargs.__dict__)
