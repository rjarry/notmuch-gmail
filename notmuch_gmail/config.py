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

import configparser
import os

import notmuch
from oauth2client.file import Storage


#------------------------------------------------------------------------------
class Config(object):

    def __init__(self, conf_file):
        parser = configparser.ConfigParser()
        parser.read_string(self.DEFAULT)
        parser.read(conf_file, encoding='utf-8')

        nm_conf_file = os.environ.get(
            'NOTMUCH_CONFIG', os.path.expanduser('~/.notmuch-config'))
        nm_parser = configparser.ConfigParser()
        nm_parser.read(nm_conf_file, encoding='utf-8')
        try:
            default_nm_db = nm_parser.get('database', 'path', fallback='~/mail')
        except configparser.NoSectionError:
            default_nm_db = '~/mail'

        self.notmuch_db_dir = parser.get(
            'core', 'notmuch_db', fallback=default_nm_db)
        self.notmuch_db_dir = os.path.expanduser(self.notmuch_db_dir)
        self.status_dir = parser.get(
            'core', 'status_dir', fallback='./.notmuch-gmail')
        self.status_dir = os.path.join(
            self.notmuch_db_dir, os.path.expanduser(self.status_dir))

        self.push_local_tags = parser.getboolean(
            'core', 'push_local_tags', fallback=True)
        self.local_wins = parser.getboolean(
            'core', 'local_wins', fallback=False)
        self.upload_drafts = parser.getboolean(
            'core', 'upload_drafts', fallback=True)
        self.upload_sent = parser.getboolean(
            'core', 'upload_sent', fallback=False)
        self.http_timeout = parser.getint(
            'core', 'http_timeout', fallback=5) or None

        self.no_sync_labels = set(parser.get(
            'ignore_labels', 'no_sync', fallback='CHATS').split())
        self.ignore_labels = set(parser.get(
            'ignore_labels', 'remote', fallback='''
            CATEGORY_FORUMS
            CATEGORY_PERSONAL
            CATEGORY_PROMOTIONS
            CATEGORY_SOCIAL
            CATEGORY_UPDATES''').split())
        self.ignore_tags = set(parser.get(
            'ignore_labels', 'local', fallback='''
            attachment
            new
            signed''').split())

        self.labels_translate = {
            'INBOX': 'inbox',
            'SPAM': 'spam',
            'TRASH': 'trash',
            'UNREAD': 'unread',
            'STARRED': 'starred',
            'IMPORTANT': 'important',
            'SENT': 'sent',
            'DRAFT': 'draft'}
        try:
            for label, tag in parser.items('labels_translate'):
                self.labels_translate[label] = tag
        except configparser.NoSectionError:
            pass
        self.tags_translate = {
            tag: label for label, tag in self.labels_translate.items()}

        self.storage_file = os.path.join(self.status_dir, 'oauth.json')
        self.storage_file = os.path.realpath(self.storage_file)
        self.history_id_file = os.path.join(self.status_dir, 'last_history_id')
        self.notmuch_rev_file = os.path.join(self.status_dir, 'last_notmuch_rev')
        self.__credentials = None
        self.__storage = None

    def __init_storage(self):
        if not os.path.exists(self.status_dir):
            os.makedirs(self.status_dir)
        if not os.path.exists(self.storage_file):
            open(self.storage_file, 'a+b').close()
        if self.__storage is None:
            self.__storage = Storage(self.storage_file)

    def get_credentials(self):
        if self.__credentials is None:
            self.__init_storage()
            self.__credentials = self.__storage.locked_get()
        return self.__credentials

    def update_credentials(self, creds):
        self.__init_storage()
        self.__storage.locked_put(creds)
        creds.set_store(self.__storage)
        self.__credentials = creds

    def get_last_history_id(self):
        try:
            with open(self.history_id_file) as f:
                last_history_id = int(f.read().strip())
            os.unlink(self.history_id_file)
            return last_history_id
        except (FileNotFoundError, ValueError):
            return None

    def update_last_history_id(self, history_id):
        if not os.path.isdir(self.status_dir):
            os.makedirs(self.status_dir)
        with open(self.history_id_file, 'w') as f:
            f.write(str(history_id))

    def get_last_notmuch_rev(self):
        try:
            with open(self.notmuch_rev_file) as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError):
            return None

    def update_last_notmuch_rev(self):
        if not os.path.isdir(self.status_dir):
            os.makedirs(self.status_dir)
        with open(self.notmuch_rev_file, 'w') as f:
            with self.notmuch_db() as db:
                rev, _ = db.get_revision()
                f.write(str(rev))

    def notmuch_db(self):
        if os.path.isdir(os.path.join(self.notmuch_db_dir, '.notmuch')):
            db = notmuch.Database(self.notmuch_db_dir,
                mode=notmuch.Database.MODE.READ_WRITE)  # @UndefinedVariable
        else:
            if not os.path.isdir(self.notmuch_db_dir):
                os.makedirs(self.notmuch_db_dir)
            db = notmuch.Database(self.notmuch_db_dir, create=True)
        if db.needs_upgrade():
            db.upgrade()
        return db

    DEFAULT= '''
# vim: ft=dosini
# This is the default configuration for notmuch-gmail.

[core]
# Folder where to store email messages in files and notmuch database.
# By default, the value is extracted from your notmuch config file located at
# NOTMUCH_CONFIG environment variable (or at ~/.notmuch-config). If a value
# is provided here, it will override the default value.
#notmuch_db = ~/mail

# Folder where to store persistent data for notmuch-gmail such as Gmail
# OAuth2 credentials and synchronization cache. Any relative path will be
# resolved against the notmuch_db path.
#status_dir = ./.notmuch-gmail

# Push local tag changes to Gmail. If set to False, any local modification will
# be overwritten by remote changes (ignoring the local_wins option).
#push_local_tags = True

# In case of conflicting changes between local and remote (tags/labels changed
# on both sides on the same messages), favor the local version and replace the
# remote version with it. By default, remote side (Gmail) wins.
#local_wins = False

# Upload local messages tagged as "draft" as Gmail DRAFT messages.
#upload_drafts = True

# Upload local messages tagged as "sent" as Gmail SENT messages (does not send
# the messages, only stores them in your Gmail account).
#upload_sent = False

# Socket timeout in seconds. 0 means use system's default system socket timeout.
#http_timeout = 5

[ignore_labels]
# Do not synchronize messages that have these Gmail labels.
#no_sync =
#\tCHATS

# Ignore the following Gmail labels (synchronize the messages without them).
#remote =
#\tCATEGORY_FORUMS
#\tCATEGORY_PERSONAL
#\tCATEGORY_PROMOTIONS
#\tCATEGORY_SOCIAL
#\tCATEGORY_UPDATES

# Ignore the following notmuch tags (synchronize the messages without them).
#local =
#\tattachment
#\tnew
#\tsigned

[labels_translate]
# Convert Gmail labels to notmuch tags (and vice versa).
# By default, only the reserved Gmail SYSTEM labels are converted
# to lower case which is all you will ever need in general.
# The syntax is: GMAIL_LABEL = notmuch_tag
#INBOX = inbox
#SPAM = spam
#TRASH = trash
#UNREAD = unread
#STARRED = starred
#IMPORTANT = important
#SENT = sent
#DRAFT = draft
'''
