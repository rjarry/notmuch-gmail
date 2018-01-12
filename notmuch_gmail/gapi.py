# This file is part of notmuch-gmail-sync.
#
# It is released under the MIT license (see the LICENSE file for more details).

import click
import httplib2
import webbrowser

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import ClientRedirectHandler
from oauth2client.tools import ClientRedirectServer
import time


#------------------------------------------------------------------------------
class GAPIError(Exception):
    pass

#------------------------------------------------------------------------------
class GmailAPI(object):

    SCOPE = 'https://www.googleapis.com/auth/gmail.modify'
    CLIENT_ID = '385492297640-2qthmiv0fbjbnlvno70aj2sgjqpd5bc4.apps.googleusercontent.com'
    CLIENT_SECRET = 'kCZu7gZqI2GD6TgNyQf_CSGm'

    def __init__(self, status):
        self.status = status
        self.service = None
        self.http = None

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

        if no_browser:
            click.echo('Open the following URL in a browser:\n\n%s' % auth_url)
            code = click.prompt('Enter verification code')
        else:
            webbrowser.open(auth_url)
            click.echo('''Your browser has been opened to visit:

    %s

If your browser is on a different machine then exit and re-run with the
--no-browser command line option.''' % auth_url)
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
        self.status.set_credentials(credentials)

    def authorize(self):
        credentials = self.status.get_credentials()
        timeout = self.status.http_timeout
        self.http = credentials.authorize(httplib2.Http(timeout=timeout))
        self.service = discovery.build('gmail', 'v1', http=self.http)

    def all_message_ids(self):
        q = ' '.join('-in:%s' % l for l in self.status.no_sync_labels)

        response = self.service.users().messages().list(
            userId='me', q=q, includeSpamTrash=True).execute()

        if 'messages' in response:
            yield response['resultSizeEstimate'], response['messages']

        while 'nextPageToken' in response:
            token = response['nextPageToken']
            response = self.service.users().messages().list(
                userId='me', q=q, includeSpamTrash=True, pageToken=token).execute()

            if 'messages' in response:
                yield response['resultSizeEstimate'], response['messages']

    def get_content(self, gmail_ids, msg_callback, fmt='raw'):
        gmail_ids = set(gmail_ids)

        def callback(msg_id, response, err):
            if err is None:
                msg_callback(response)
            else:
                if isinstance(err, HttpError) and err.resp.status in (400, 404):
                    # bad message request, ignore
                    pass
                else:
                    raise err
            gmail_ids.discard(msg_id)

        fields = 'id,historyId,labelIds'
        if fmt == 'raw':
            fields += ',raw'

        batch_size = max_batch_size = 64
        good_batches = conn_errors = pause = 0

        while gmail_ids:
            if pause > 0:
                time.sleep(pause)

            batch = self.service.new_batch_http_request(callback=callback)

            for gmail_id in gmail_ids:
                request = self.service.users().messages().get(
                    userId='me', id=gmail_id, format=fmt, fields=fields)
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
                    pause = 1 + pause * 2
                    # reduce batch size
                    batch_size = batch_size // 2
                else:
                    raise

            except ConnectionError:
                conn_errors += 1
                if conn_errors > 10:
                    raise
                pause = 1 + pause * 2
