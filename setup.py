# This file is part of notmuch-gmail-sync.
#
# It is released under the MIT license (see the LICENSE file for more details).

import io
import setuptools
import notmuch_gmail


with io.open('README', encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()

setuptools.setup(
    name = 'notmuch-gmail-sync',
    version = notmuch_gmail.VERSION,
    description = 'Bidirectional sync of Gmail messages with notmuch database',
    long_description = LONG_DESCRIPTION,
    url = 'https://github.com/rjarry/notmuch-gmail-sync',
    license = 'MIT',
    author = 'Robin Jarry',
    author_email = 'robin@jarry.cc',
    keywords = ['notmuch', 'gmail', 'notmuchmail', 'oauth2', 'email'],
    classifiers = [
        'Development Status :: 1 - Planning',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Communications :: Email :: Email Clients (MUA)',
    ],
    python_requires = '>= 3.3',
    install_requires = [
        'click',
        'google-api-python-client',
        'oauth2client',
    ],
    packages = setuptools.find_packages(),
    zip_safe = False,
    include_package_data = True,
    entry_points = {
        'console_scripts': ['notmuch-gmail = notmuch_gmail.__main__:main'],
    },
)
