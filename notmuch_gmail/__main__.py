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

import click
import os

from .status import Status
from .gapi import GmailAPI


#------------------------------------------------------------------------------
@click.group()
@click.option('--config', '-c',
              help='Path to config file',
              envvar='NOTMUCH_GMAIL_CONFIG',
              type=click.Path(dir_okay=False),
              default='~/.notmuch-gmail-config', show_default=True)
@click.pass_context
def main(ctx, config):
    """
    Bidirectional sync of Gmail messages with a notmuch database.
    """
    os.umask(0o077)  # only create user readable/writable files and folders
    ctx.obj = Status(os.path.expanduser(config))

#------------------------------------------------------------------------------
@main.command(short_help='Authenticate against Gmail servers')
@click.option('--no-browser', '-n',
              help='Do not try to open a web browser for authentication',
              is_flag=True)
@click.option('--force', '-f',
              help='Ignore existing credentials',
              is_flag=True)
@click.pass_obj
def auth(status, no_browser, force):
    credentials = status.get_credentials()
    if force or not credentials or credentials.invalid:
        api = GmailAPI(status)
        api.authenticate(no_browser)
    else:
        click.echo('You are already authenticated.')

#------------------------------------------------------------------------------
@main.command(short_help='Pull emails from Gmail servers')
@click.option('--no-browser', '-n',
              help='Do not try to open a web browser for authentication',
              is_flag=True)
@click.pass_obj
def pull(status, no_browser):
    api = GmailAPI(status)
    credentials = status.get_credentials()
    if not credentials or credentials.invalid:
        api.authenticate(no_browser)

    api.authorize()

    history_id = status.cache.get_history_id()

    # first pull, no cache
    bar = click.progressbar(label='Fetching message IDs', width=0,
                            length=1, show_percent=True)
    with bar:
        for total, msgs in api.all_message_ids():
            bar.length = total
            status.cache.add_gmail_ids(m['id'] for m in msgs)
            bar.update(1)
        bar.update(bar.length - bar.pos)

    total = status.cache.new_gmail_ids_count()
    click.echo('%d new messages' % total)

    bar = click.progressbar(label='Fetching message contents', width=0,
                            length=total, show_percent=True)
    with bar:
        new_ids = status.cache.new_gmail_ids()
        def callback(msg):
            click.echo(msg['id'])
            bar.update(1)
        
        api.get_content(new_ids, callback, fmt='minimal')
        
        bar.update(bar.length - bar.pos)
        
        
#------------------------------------------------------------------------------
@main.command(short_help='Print default config')
def defconfig():
    """
    Print the default configuration to standard output.

    Redirect output to ~/.notmuch-gmail-config and modify the
    file according to your needs.
    """
    click.echo(Status.DEFAULT_CONFIG.strip())
