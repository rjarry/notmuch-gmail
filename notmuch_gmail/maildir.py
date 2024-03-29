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

import base64
import logging
import os
import re

from notmuch.errors import NotmuchError


LOG = logging.getLogger(__name__)

#------------------------------------------------------------------------------
class Maildir(object):

    def __init__(self, config):
        self.config = config
        gmail_dir = os.path.join(self.config.notmuch_db_dir, 'gmail')
        self.tmp_dir = os.path.join(gmail_dir, 'tmp')
        self.new_dir = os.path.join(gmail_dir, 'new')
        self.cur_dir = os.path.join(gmail_dir, 'cur')

    def get_changes(self):
        last_rev = self.config.get_last_notmuch_rev()
        if last_rev is not None:
            return self._search_notmuch('lastmod:%s..' % last_rev)
        return {}, {}

    def all_messages(self):
        return self._search_notmuch('path:**')[0]

    GMAIL_MESSAGE_RE = re.compile(r'^gmail\.([0-9a-f]+):2,[PRSTDF]?$')

    def _search_notmuch(self, querystring):
        gmail = {}
        local = {}

        with self.config.notmuch_db() as db:
            query = db.create_query(querystring)
            for notmuch_msg in query.search_messages():
                for f in notmuch_msg.get_filenames():
                    fname = os.path.basename(f)
                    match = self.GMAIL_MESSAGE_RE.match(fname)
                    tags = set(notmuch_msg.get_tags())
                    tags.difference_update(self.config.ignore_tags)
                    if match:
                        gmail_id = match.group(1)
                        gmail[gmail_id] = tags
                    else:
                        local[f] = tags

        return gmail, local

    def store(self, gmail_msg):
        filename = 'gmail.{id}:2,'.format(**gmail_msg)

        tmp_path = os.path.join(self.tmp_dir, filename)
        if not os.path.isdir(self.tmp_dir):
            os.makedirs(self.tmp_dir)
        if not os.path.isdir(self.cur_dir):
            os.makedirs(self.cur_dir)

        msg_bytes = base64.urlsafe_b64decode(gmail_msg['raw'].encode('ascii'))
        with open(tmp_path, 'wb') as f:
            f.write(msg_bytes)

        msg_path = os.path.join(self.new_dir, filename)
        if not os.path.isdir(self.new_dir):
            os.makedirs(self.new_dir)
        os.rename(tmp_path, msg_path)

        try:
            utime = int(gmail_msg['internalDate']) / 1000
            os.utime(msg_path, times=(utime, utime))
        except:
            pass

        return msg_path

    def index(self, messages):
        with self.config.notmuch_db() as db:
            for msg_path, tags in messages.items():
                msg, _ = db.add_message(msg_path, sync_maildir_flags=False)
                msg.freeze()
                for tag in tags:
                    msg.add_tag(tag, sync_maildir_flags=False)
                msg.thaw()

    def apply_tags(self, remote_updated):
        n_updated = len(remote_updated)
        counter = '[%{0}d/%{0}d]'.format(len(str(n_updated)))
        n = 0
        with self.config.notmuch_db() as db:
            for gmail_id, tags in remote_updated.items():
                n += 1
                fpath = os.path.join(self.new_dir, 'gmail.{}:2,'.format(gmail_id))
                msg = db.find_message_by_filename(fpath)
                if msg is None:
                    LOG.warning(
                        counter + ' message %r not found in notmuch db',
                        n, n_updated, fpath)
                    continue
                msg.freeze()
                msg.remove_all_tags(sync_maildir_flags=False)
                for tag in tags:
                    msg.add_tag(tag, sync_maildir_flags=False)
                msg.thaw()
                LOG.info(counter + ' message %r tags %s updated',
                         n, n_updated, gmail_id, tags)

    def delete(self, remote_deleted):
        n_deleted = len(remote_deleted)
        counter = '[%{0}d/%{0}d]'.format(len(str(n_deleted)))
        n = 0
        with self.config.notmuch_db() as db:
            for gmail_id in remote_deleted:
                n += 1
                fpath = os.path.join(self.new_dir, 'gmail.{}:2,'.format(gmail_id))
                try:
                    db.remove_message(fpath)
                except NotmuchError as e:
                    LOG.warning('Message %r: %s', fpath, e)

                if os.path.isfile(fpath):
                    os.unlink(fpath)

                LOG.info(counter + ' message %r deleted', n, n_deleted, gmail_id)
