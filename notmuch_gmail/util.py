# Copyright (c) 2018 Robin Jarry
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging.config


#------------------------------------------------------------------------------
UNITS = ['B', 'K', 'M', 'G', 'T', 'P', 'E']
def human_size(size):
    try:
        if size < 1000:
            return str(size)
        else:
            u = 0
            while size >= 1000 and u < len(UNITS):
                size /= 1000
                u += 1
            return '%.1f%s' % (size, UNITS[u])
    except:
        return size

#------------------------------------------------------------------------------
def configure_logging(verbose=0):
    logging.config.dictConfig({
        'version': 1,
        'reset_existing_loggers': True,
        'formatters': {
            'simple': {
                'format': '%(asctime)s %(levelname)s %(message)s',
                'datefmt': '%H:%M:%S',
            },
        },
        'handlers': {
            'stdout': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
                'formatter': 'simple',
                'level': 'DEBUG',
            },
        },
        'root': {
            'handlers': ['stdout'],
            'level': 'DEBUG' if verbose > 0 else 'INFO',
        },
        'loggers': {
            'notmuch_gmail': {
                'handlers': ['stdout'],
                'level': 'DEBUG' if verbose > 0 else 'INFO',
                'propagate': False,
            },
            'googleapiclient': {
                'handlers': ['stdout'],
                'level': 'DEBUG' if verbose > 1 else 'WARNING',
                'propagate': False,
            },
        },
    })

    logging.addLevelName(logging.ERROR, 'E')
    logging.addLevelName(logging.WARNING, 'W')
    logging.addLevelName(logging.INFO, 'I')
    logging.addLevelName(logging.DEBUG, 'D')
