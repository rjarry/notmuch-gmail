# This file is part of notmuch-gmail-sync.
#
# It is released under the MIT license (see the LICENSE file for more details).

all: virtualenv

src_archive:
	python3 ./setup.py sdist

wheel_archive:
	python3 ./setup.py bdist_wheel

virtualenv: .venv/bin/activate
	ENV=.venv/bin/activate /bin/sh -li

.venv/bin/activate:
	virtualenv -p python3 --system-site-packages .venv
	.venv/bin/pip install -e .
