# This file is part of notmuch-gmail-sync.
#
# It is released under the MIT license (see the LICENSE file for more details).

import os
import sqlite3


#------------------------------------------------------------------------------
class Cache(object):

    def __init__(self, db_filename):
        self.db_filename = db_filename
        self.connection = None

    INIT_DB_SQL = '''
    PRAGMA foreign_keys = ON;
    CREATE TABLE IF NOT EXISTS gmail(
        id text PRIMARY KEY
    );
    CREATE TABLE IF NOT EXISTS notmuch(
        id integer PRIMARY KEY
    );
    CREATE TABLE IF NOT EXISTS links(
        gmail_id text f REFERENCES gmail(id) ON DELETE CASCADE,
        notmuch_id integer REFERENCES notmuch(id) ON DELETE CASCADE
    );
    CREATE UNIQUE INDEX IF NOT EXISTS gmail_id_idx ON links(gmail_id);
    CREATE UNIQUE INDEX IF NOT EXISTS notmuch_id_idx ON links(notmuch_id);
    CREATE TABLE IF NOT EXISTS misc(
        name text PRIMARY KEY DEFAULT "history_id",
        value integer DEFAULT 0
    );
    INSERT OR IGNORE INTO misc DEFAULT VALUES;
    '''

    def __init_db(self):
        db_dir = os.path.dirname(self.db_filename)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

        self.connection = sqlite3.connect(self.db_filename)  # @UndefinedVariable

        with self.connection:
            self.connection.executescript(self.INIT_DB_SQL)

    def __del__(self):
        if self.connection is not None:
            with self.connection:
                self.connection.execute('VACUUM')
            self.connection.close()
            self.connection = None

    def get_history_id(self):
        if self.connection is None:
            self.__init_db()
        cursor = self.connection.execute(
            'SELECT value FROM misc WHERE name = "history_id"')
        return cursor.fetchone()[0]

    def set_history_id(self, history_id):
        if self.connection is None:
            self.__init_db()
        with self.connection:
            self.connection.execute(
                'UPDATE misc SET value = ? WHERE name = "history_id"',
                [history_id])

    def add_gmail_ids(self, gmail_ids):
        if self.connection is None:
            self.__init_db()
        with self.connection:
            cursor = self.connection.executemany(
                'INSERT OR IGNORE INTO gmail(id) values (?)',
                ((i,) for i in gmail_ids))
            return cursor.rowcount

    def new_gmail_ids_count(self):
        if self.connection is None:
            self.__init_db()
        cursor = self.connection.execute(
            '''SELECT count(id) FROM gmail
               WHERE NOT EXISTS (SELECT 1 FROM links WHERE gmail_id = id);''')
        return cursor.fetchone()[0]

    def new_gmail_ids(self):
        if self.connection is None:
            self.__init_db()
        cursor = self.connection.execute(
            '''SELECT id FROM gmail
               WHERE NOT EXISTS (SELECT 1 FROM links WHERE gmail_id = id);''')
        for row in cursor:
            yield row[0]
