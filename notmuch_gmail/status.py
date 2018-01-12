# This file is part of notmuch-gmail-sync.
#
# It is released under the MIT license (see the LICENSE file for more details).

import configparser
import os

from oauth2client.file import Storage

from .cache import Cache


#------------------------------------------------------------------------------
class Status(object):

    def __init__(self, conf_file):
        parser = configparser.ConfigParser()
        parser.read_string(self.DEFAULT_CONFIG)
        parser.read(conf_file, encoding='utf-8')

        self.notmuch_db = parser.get('core', 'notmuch_db', fallback='~/mail')
        self.notmuch_db = os.path.expanduser(self.notmuch_db)
        self.status_dir = parser.get('core', 'status_dir',
                                     fallback='~/mail/.notmuch-gmail')
        self.status_dir = os.path.expanduser(self.status_dir)
        self.upload_drafts = parser.getboolean('core', 'upload_drafts')
        self.upload_sent = parser.getboolean('core', 'upload_sent')
        self.http_timeout = parser.getint('core', 'http_timeout') or None

        self.no_sync_labels = parser.get('ignore_labels', 'no_sync',
                                         fallback='').split()
        self.ignore_labels = parser.get('ignore_labels', 'remote',
                                        fallback='').split()
        self.ignore_tags = parser.get('ignore_labels', 'local',
                                      fallback='').split()

        self.cache = Cache(os.path.join(self.status_dir, 'cache.sqlite'))

        self.__storage_file = os.path.join(self.status_dir, 'oauth.json')
        self.__storage_file = os.path.realpath(self.__storage_file)
        self.__storage = None
        self.__credentials = None

    def __init_storage(self):
        if not os.path.exists(self.status_dir):
            os.makedirs(self.status_dir)
        if not os.path.exists(self.__storage_file):
            open(self.__storage_file, 'a+b').close()
        if self.__storage is None:
            self.__storage = Storage(self.__storage_file)

    def get_credentials(self):
        if self.__credentials is None:
            self.__init_storage()
            self.__credentials = self.__storage.locked_get()
        return self.__credentials

    def set_credentials(self, creds):
        self.__init_storage()
        self.__storage.locked_put(creds)
        creds.set_store(self.__storage)
        self.__credentials = creds

    DEFAULT_CONFIG = '''\
# vim: ft=dosini
# This is the default configuration for notmuch-gmail.

[core]
# Folder where to store email messages in files and notmuch database.
notmuch_db = ~/mail

# Folder where to store persistent data for notmuch-gmail
# such as Gmail OAuth2 credentials and synchronization cache.
status_dir = %(notmuch_db)s/.notmuch-gmail

# Upload local messages tagged as "draft" as Gmail DRAFT messages.
upload_drafts = True

# Upload local messages tagged as "sent" as Gmail SENT messages (does not send
# the messages, only stores them in your Gmail account).
upload_sent = True

# Socket timeout in seconds.
http_timeout = 5

[ignore_labels]
# Do not synchronize messages that have these Gmail labels.
no_sync =
\tCHATS

# Ignore the following Gmail labels (synchronize the messages without them).
remote =
\tCATEGORY_FORUMS
\tCATEGORY_PERSONAL
\tCATEGORY_PROMOTIONS
\tCATEGORY_SOCIAL
\tCATEGORY_UPDATES

# Ignore the following notmuch tags (synchronize the messages without them).
#local =
#\tattachment
#\tencrypted
#\tmute
#\tmuted
#\tnew
#\tpassed
#\treplied
#\tsigned
#\ttodo
'''
