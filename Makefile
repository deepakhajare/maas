PYTHON_SRC := $(shell find src -name '*.py' )
PYTHON = python

build: bin/buildout

bin/buildout: buildout.cfg setup.py
	$(PYTHON) bootstrap.py
	bin/buildout
	@touch bin/buildout

dev-db:
	bin/maasdb start ./db/ disposable

test: dev-db
	bin/test

lint:
	pyflakes $(PYTHON_SRC)
	pylint --rcfile=etc/pylintrc $(PYTHON_SRC)

check: clean bin/buildout dev-db
	bin/test

clean:
	find . -type f -name '*.py[co]' -exec $(RM) {} \;
	$(RM) bin/buildout bin/django bin/test

distclean: clean
	bin/maasdb delete-cluster ./db/
	$(RM) -r eggs develop-eggs
	$(RM) -r build logs parts
	$(RM) tags TAGS .installed.cfg
	$(RM) *.egg *.egg-info

tags:
	bin/tags

run: build dev-db
	bin/django runserver 8000

harness: build dev-db
	bin/django shell

syncdb: build dev-db
	bin/django syncdb
