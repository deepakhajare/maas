PYTHON = python2.7

build: bin/buildout bin/django doc

bin/buildout: bootstrap.py distribute_setup.py
	$(PYTHON) bootstrap.py --distribute --setup-source distribute_setup.py

bin/django bin/django-python bin/sphinx bin/test: \
    bin/buildout buildout.cfg setup.py
	bin/buildout

dev-db:
	bin/maasdb start ./db/ disposable

test: bin/test
	bin/test

lint: sources = setup.py src templates utilities
lint:
	@bin/flake8 $(sources) | \
	    (fgrep -v "from maas.settings import *" || true)

check: clean test

docs/api.rst: bin/django src/maasserver/api.py
	bin/django gen_rst_api_doc > $@

doc: bin/sphinx docs/api.rst
	bin/sphinx

clean:
	find . -type f -name '*.py[co]' -print0 | xargs -r0 $(RM)
	$(RM) bin/buildout bin/django bin/django-python bin/test bin/flake8
	$(RM) bin/sphinx bin/sphinx-build bin/sphinx-quickstart

distclean: clean
	bin/maasdb delete-cluster ./db/
	$(RM) -r eggs develop-eggs
	$(RM) -r build logs parts
	$(RM) tags TAGS .installed.cfg
	$(RM) *.egg *.egg-info
	$(RM) docs/api.rst
	$(RM) -r docs/_build/

run: bin/django dev-db
	bin/django runserver 8000

harness: bin/django dev-db
	bin/django shell

syncdb: bin/django dev-db
	bin/django syncdb

.PHONY: \
    build check clean dev-db distclean doc \
    harness lint run syncdb test
