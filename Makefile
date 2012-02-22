PYTHON = python2.7

build: \
    bin/buildout \
    bin/maas bin/test.maas \
    bin/twistd.pserv bin/test.pserv \
    bin/py bin/ipy

all: build doc

bin/buildout: bootstrap.py distribute_setup.py
	$(PYTHON) bootstrap.py --distribute --setup-source distribute_setup.py
	@touch --no-create $@  # Ensure it's newer than its dependencies.

bin/maas: bin/buildout buildout.cfg setup.py
	bin/buildout install maas
	@touch --no-create $@

bin/test.maas: bin/buildout buildout.cfg setup.py
	bin/buildout install maas-test
	@touch --no-create $@

bin/twistd.pserv: bin/buildout buildout.cfg setup.py
	bin/buildout install pserv
	@touch --no-create $@

bin/test.pserv: bin/buildout buildout.cfg setup.py
	bin/buildout install pserv-test
	@touch --no-create $@

bin/flake8: bin/buildout buildout.cfg setup.py
	bin/buildout install flake8
	@touch --no-create $@

bin/sphinx: bin/buildout buildout.cfg setup.py
	bin/buildout install sphinx
	@touch --no-create $@

bin/py bin/ipy: bin/buildout buildout.cfg setup.py
	bin/buildout install repl
	@touch --no-create bin/py bin/ipy

dev-db:
	utilities/maasdb start ./db/ disposable

test: bin/test.maas bin/test.pserv
	bin/test.maas
	bin/test.pserv

lint: sources = setup.py src templates utilities
lint: bin/flake8
	@bin/flake8 $(sources) | \
	    (! egrep -v "from maas[.](settings|development) import [*]")

check: clean test

docs/api.rst: bin/maas src/maasserver/api.py
	bin/maas generate_api_doc > $@

sampledata: bin/maas syncdb
	bin/maas loaddata src/maasserver/fixtures/dev_fixture.yaml

doc: bin/sphinx docs/api.rst
	bin/sphinx

clean:
	find . -type f -name '*.py[co]' -print0 | xargs -r0 $(RM)
	find . -type f -name '*~' -print0 | xargs -r0 $(RM)

distclean: clean shutdown
	utilities/maasdb delete-cluster ./db/
	$(RM) -r eggs develop-eggs
	$(RM) -r bin build dist logs parts
	$(RM) tags TAGS .installed.cfg
	$(RM) -r *.egg *.egg-info src/*.egg-info
	$(RM) docs/api.rst
	$(RM) -r docs/_build/
	$(RM) -r services/*/supervise
	$(RM) twisted/plugins/dropin.cache

harness: bin/maas dev-db
	bin/maas shell

syncdb: bin/maas dev-db
	bin/maas syncdb --noinput

services := api pserv
services := $(patsubst %,services/%/,$(services))

# The services/*/@something targets below are phony - they will never
# correspond to an existing file - but we want them to be evaluated
# for building.

start: $(addsuffix @start,$(services))

stop: $(addsuffix @stop,$(services))

run: start
	@tail --follow=name logs/*/current

status: $(addsuffix @status,$(services))

shutdown: $(addsuffix @shutdown,$(services))

services/%/@supervise: services/%/@deps logs/%
	@if ! svok $(@D); then \
	    logdir=$(PWD)/logs/$* supervise $(@D) & fi
	@while ! svok $(@D); do sleep 0.1; done

services/%/@start: services/%/@supervise
	@svc -u $(@D)

services/%/@stop: services/%/@supervise
	@svc -d $(@D)

services/%/@shutdown:
	@if svok $(@D); then svc -dx $(@D); fi
	@while svok $(@D); do sleep 0.1; done

services/%/@status:
	@svstat $(@D)

services/pserv/@deps: bin/twistd.pserv

services/api/@deps: bin/maas dev-db

.PRECIOUS: logs/%
logs/%:
	@mkdir -p $@

.PHONY: \
    build check clean dev-db distclean doc \
    harness lint run shutdown syncdb test \
    sampledata start stop status
