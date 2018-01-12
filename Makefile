# This file is part of notmuch-gmail-sync.
#
# It is released under the MIT license (see the LICENSE file for more details).

all: src_archive

src_archive:
	python3 ./setup.py sdist
