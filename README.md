# notmuch-gmail

Bidirectional sync of Gmail messages with a notmuch database.

![Logo](logo.png)

## Description

`notmuch-gmail` is a command line application that can pull email and labels
(and changes to labels) from your Gmail account and store them locally in a
maildir with the labels synchronized with a notmuch database. The changes to
tags in the notmuch database may be pushed back remotely to your Gmail account.

## Installation

```
git clone https://git.sr.ht/~rjarry/notmuch-gmail
cd notmuch-gmail
python3 -m pip install -e .
```

NB: notmuch python bindings must be installed first (e.g. `apt install
python3-notmuch`)

## Quickstart

Run this in a terminal and follow the instructions:

```
notmuch-gmail
```

The first sync will take a long time. After which you should run the same
command in your user's crontab:

```
*/5 * * * * notmuch-gmail --logfile ~/.notmuch-gmail.log
```

Or run it manually when needed.

## Configuration & Advanced Usage

The default configuration file is loaded from `~/.notmuch-gmail-config`. You
can initialize the file with the following command:

```
notmuch-gmail --defconfig > ~/.notmuch-gmail-config
```

And open it with an editor.

## Privacy Policy

* `notmuch-gmail` is a **local** command line application. It uses OAuth2 to
  access your Gmail data and will **NOT** share anything with anyone.

* `notmuch-gmail` uses the Gmail web API to access (READ) your messages and
  labels.

* `notmuch-gmail` uses the Gmail web API to change (ADD, REMOVE) the labels
  associated with messages.

* `notmuch-gmail` uses the Gmail web API to change (ADD, REMOVE) your Gmail
  labels.

* `notmuch-gmail` uses the Gmail web API to add (INSERT) new DRAFT and SENT
  messages.

* `notmuch-gmail` will not and can not:

  - Add or delete messages on your remote account (except syncing the `trash`
    or `spam` label to messages, and those messages will eventually be
    [deleted](https://support.google.com/mail/answer/7401?co=GENIE.Platform%3DDesktop&hl=en))

  - Modify messages other than their labels

* `notmuch-gmail` is free software released under the [MIT
  license](https://opensource.org/licenses/MIT) and comes with **NO
  WARRANTIES**.
