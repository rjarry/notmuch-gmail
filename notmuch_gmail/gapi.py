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

import functools
import httplib2
import logging
import time
import webbrowser

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import ClientRedirectHandler, ClientRedirectServer


LOG = logging.getLogger(__name__)

#------------------------------------------------------------------------------
class GAPIError(Exception):
    pass

#------------------------------------------------------------------------------
class NoSyncError(GAPIError):
    pass

#------------------------------------------------------------------------------
class GmailAPI(object):

    SCOPE = 'https://www.googleapis.com/auth/gmail.modify'
    # These are not really secret. Only used to identify the application.
    CLIENT_ID = '504761708784-b77ce00710hrdho8iba9emq6dkqfbvgo.apps.googleusercontent.com'
    CLIENT_SECRET = '6WjLoK_qUn7mQNZjz6LVI5JT'

    def __init__(self, config):
        self.config = config
        self.service = None
        self.http = None
        self.labels = {}
        self.label_ids = {}

    def authenticate(self, no_browser=False):
        if no_browser:
            httpd = None
            redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        else:
            httpd = ClientRedirectServer(('localhost', 0), ClientRedirectHandler)
            redirect_uri = 'http://localhost:%d/' % httpd.server_port

        flow = OAuth2WebServerFlow(client_id=self.CLIENT_ID,
                                   client_secret=self.CLIENT_SECRET,
                                   scope=self.SCOPE,
                                   redirect_uri=redirect_uri)

        auth_url = flow.step1_get_authorize_url()

        if httpd is None:
            print('Open the following URL in a browser:\n\n%s' % auth_url)
            code = input('Enter verification code: ').strip()
        else:
            webbrowser.open(auth_url)
            print('Your browser has been opened to visit:\n\n%s\n' % auth_url)
            print('If your browser is on a different machine, then exit '
                  'and re-run with the --no-browser command line option.')
            try:
                httpd.handle_request()
            finally:
                httpd.server_close()
            if 'error' in httpd.query_params:
                raise GAPIError('Authentication request was rejected.')
            if 'code' in httpd.query_params:
                code = httpd.query_params['code']
            else:
                raise GAPIError('Failed to retreive verification code. '
                                'Try running with --no-browser.')

        credentials = flow.step2_exchange(code)
        self.config.update_credentials(credentials)

    def authorize(self):
        credentials = self.config.get_credentials()
        timeout = self.config.http_timeout
        self.http = credentials.authorize(httplib2.Http(timeout=timeout))
        self.service = discovery.build('gmail', 'v1', http=self.http)

    def update_labels(self):
        response = self.service.users().labels().list(userId='me').execute()
        self.labels = {}
        self.label_ids = {}
        for label in response['labels']:
            self.labels[label['id']] = label['name']
            self.label_ids[label['name']] = label['id']

    def create_label(self, name):
        response = self.service.users().labels().create(
            userId='me', name=name, labelListVisibility='labelShow',
            messageListVisibility='show').execute()
        self.labels[response['id']] = response['name']
        self.label_ids[response['name']] = response['id']
        return response['id']

    def _message_tags(self, message):
        tags = set()
        if 'labelIds' not in message:
            return tags

        for label_id in message['labelIds']:
            label = self.labels.get(label_id)
            if label is None or label in self.config.ignore_labels:
                continue
            if label in self.config.no_sync_labels:
                raise NoSyncError(
                    'message %r not synced (label %r)' % (message['id'], label))
            tag = self.config.labels_translate.get(label, label)
            if tag in self.config.ignore_tags:
                continue
            tags.append(tag)

        return tags

    def get_changes(self, last_history_id):
        updated = {}
        new = set()
        deleted = set()

        def update(msg):
            i = msg['id']
            if i in new or i in deleted:
                return
            updated[i] = self._message_tags(msg)

        def add(msg):
            # result is ignored, only to check if message should be synced
            self._message_tags(msg)
            i = msg['id']
            updated.pop(i, None)
            deleted.discard(i)
            new.add(i)

        def delete(msg):
            # result is ignored, only to check if message should be synced
            self._message_tags(msg)
            i = msg['id']
            updated.pop(i, None)
            new.discard(i)
            deleted.add(i)

        callbacks = {
            'messagesAdded': add,
            'messagesDeleted': delete,
            'labelsAdded': update,
            'labelsRemoved': update,
            }

        for changes in self._history(last_history_id):
            for ch in changes:
                for field, callback in callbacks.items():
                    for item in ch.get(field, []):
                        try:
                            callback(item['message'])
                        except NoSyncError:
                            pass

        return updated, new, deleted

    def _history(self, start_id):
        fields = 'messagesAdded,messagesDeleted,labelsAdded,labelsDeleted'

        try:
            response = self.service.users().history().list(
                userId='me', startHistoryId=start_id, fields=fields).execute()
        except HttpError as e:
            if e.resp.status == 404:
                raise GAPIError('start_id is too old') from e
            else:
                raise

        if 'history' in response:
            yield response['history']

        while 'nextPageToken' in response:
            tok = response['nextPageToken']
            response = self.service.users().history().list(
                userId='me', startHistoryId=start_id,
                fields=fields, pageToken=tok).execute()

            if 'history' in response:
                yield response['history']

    def all_ids(self):
        q = ' '.join('-in:%s' % l for l in self.config.no_sync_labels)
        fields = 'nextPageToken,resultSizeEstimate,messages/id'

        response = self.service.users().messages().list(
            userId='me', q=q, includeSpamTrash=True, fields=fields).execute()

        if 'messages' in response:
            ids = [m['id'] for m in response['messages']]
            yield response['resultSizeEstimate'], ids

        while 'nextPageToken' in response:
            tok = response['nextPageToken']
            response = self.service.users().messages().list(
                userId='me', q=q, includeSpamTrash=True,
                fields=fields, pageToken=tok).execute()

            if 'messages' in response:
                ids = [m['id'] for m in response['messages']]
                yield response['resultSizeEstimate'], ids

    def get_content(self, gmail_ids, msg_callback, fmt='minimal'):
        fields = 'id,labelIds'
        if fmt == 'raw':
            fields += ',internalDate,raw,sizeEstimate'

        req_template = functools.partial(
            self.service.users().messages().get,
            userId='me', format=fmt, fields=fields,
            )

        items = {i: {} for i in gmail_ids}
        self._batch(items, req_template, msg_callback)

    def push_tags(self, local_updated, msg_callback):
        LOG.info('Resolving tag changes on local messages...')
        modify_ops = {}
        n_updated = len(local_updated)
        counter = '[%{0}d/%{0}d]'.format(len(str(n_updated)))
        n = 0
        def callback_fetch(remote_msg):
            nonlocal n
            n += 1
            gmail_id = remote_msg['id']
            local_tags = local_updated[gmail_id]
            remote_tags = remote_msg['tags']
            add_tags = local_tags - remote_tags
            rm_tags = remote_tags - local_tags
            add_lids = []
            rm_lids = []

            for tags, lids in (add_tags, add_lids), (rm_tags, rm_lids):
                for t in tags:
                    label = self.config.tags_translate.get(t, t)
                    if label in self.label_ids:
                        lids.append(self.label_ids.get(label))
                    else:
                        lids.append(self.create_label(label))

            if add_lids or rm_lids:
                op = {'addLabelIds': add_lids, 'removeLabelIds': rm_lids}
                modify_ops[gmail_id] = op
                LOG.info(counter + ' message %r %s',
                         n, n_updated, gmail_id, op)
            else:
                LOG.info(counter + ' message %r no changes',
                         n, n_updated, gmail_id)

        req_template = functools.partial(
            self.service.users().messages().get,
            userId='me', format='minimal', fields='id,labelIds',
            )
        items = {i: {} for i in local_updated}
        self._batch(items, req_template, callback_fetch)

        n_ops = len(modify_ops)
        LOG.info('Pushing label changes...', n_ops)
        counter = '[%{0}d/%{0}d]'.format(len(str(n_updated)))
        n = 0
        def callback_push(msg):
            nonlocal n
            n += 1
            LOG.info(counter + ' message %r labels updated',
                     n, n_ops, msg['id'])

        req_template = functools.partial(
            self.service.users().messages().modify,
            userId='me', fields='id',
            )
        self._batch(modify_ops, req_template, callback_push)

    def _batch(self, items, req_template, msg_callback):

        def callback(req_id, message, err):
            if err is None:
                try:
                    message['tags'] = self._message_tags(message)
                    msg_callback(message)
                except NoSyncError:
                    pass
            else:
                if isinstance(err, HttpError) and err.resp.status in (400, 404):
                    pass  # bad message request, ignore
                else:
                    raise err
            del items[req_id]

        batch_size = max_batch_size = 50
        good_batches = conn_errors = pause = 0

        while items:
            if pause > 0:
                time.sleep(pause)

            batch = self.service.new_batch_http_request(callback=callback)

            for gmail_id, kwargs in items.items():
                request = req_template(id=gmail_id, **kwargs)
                batch.add(request, request_id=gmail_id)
                if len(batch._order) >= batch_size:
                    break

            try:
                batch.execute(http=self.http)

                if good_batches > 10:
                    pause = pause // 2
                    batch_size = max(batch_size * 2, max_batch_size)
                    good_batches = 0
                conn_errors = 0

            except HttpError as e:
                if e.resp.status in (403, 429):
                    # increase pause duration before new batch
                    pause = max(1 + pause * 2, 30)
                    # reduce batch size
                    batch_size = min(batch_size // 2, 1)
                else:
                    raise

            except ConnectionError as e:
                conn_errors += 1
                if conn_errors > 10:
                    raise
                pause = 1 + pause * 2
