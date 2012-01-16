PYTHON_SRC := $(shell find src -name '*.py' )
PYTHON = python

build: bin/buildout
	bin/maasdb start ./db/ disposable

bin/buildout: buildout.cfg setup.py
	$(PYTHON) bootstrap.py
	bin/buildout
	@touch bin/buildout

test:
	bin/test

lint:
	pyflakes $(PYTHON_SRC)
	pylint --rcfile=etc/pylintrc $(PYTHON_SRC)

check: clean bin/buildout
	bin/test

clean:
	find . -type f -name '*.py[co]' -exec rm -f {} \;
	rm -f bin/buildout
	#bzr clean-tree --unknown --force

distclean: clean
	bin/maasdb delete-cluster ./db/
	rm -rf download-cache
	rm -rf eggs
	rm -rf develop-eggs

tags:
	bin/tags

run: build
	bin/django runserver 8000

harness:
	bin/maasdb start ./db/ disposable
	bin/django shell

syncdb:
	bin/maasdb start ./db/ disposable
	bin/django syncdb
