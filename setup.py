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

import setuptools


setuptools.setup(
    name = 'notmuch-gmail',
    version = __import__('notmuch_gmail').VERSION,
    description = 'Bidirectional sync of Gmail messages with a notmuch database',
    long_description = open('README', encoding='utf-8').read(),
    url = 'https://github.com/rjarry/notmuch-gmail',
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
