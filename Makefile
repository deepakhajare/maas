PYTHON = python2.7

build: \
    bin/buildout \
    bin/maas bin/test.maas \
    bin/twistd.pserv bin/test.pserv \
    bin/twistd.txlongpoll \
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

bin/twistd.txlongpoll: bin/buildout buildout.cfg setup.py
	bin/buildout install txlongpoll
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

lint: sources = contrib setup.py src templates twisted utilities
lint: bin/flake8
	@find $(sources) -name '*.py' ! -path '*/migrations/*' \
	    -print0 | xargs -r0 bin/flake8

check: clean test

docs/api.rst: bin/maas src/maasserver/api.py syncdb
	bin/maas generate_api_doc > $@

sampledata: bin/maas syncdb
	bin/maas loaddata src/maasserver/fixtures/dev_fixture.yaml

doc: bin/sphinx docs/api.rst
	bin/sphinx

clean:
	find . -type f -name '*.py[co]' -print0 | xargs -r0 $(RM)
	find . -type f -name '*~' -print0 | xargs -r0 $(RM)
	$(RM) -r media/demo/* media/development

distclean: clean shutdown
	utilities/maasdb delete-cluster ./db/
	$(RM) -r eggs develop-eggs
	$(RM) -r bin build dist logs/* parts
	$(RM) tags TAGS .installed.cfg
	$(RM) -r *.egg *.egg-info src/*.egg-info
	$(RM) docs/api.rst
	$(RM) -r docs/_build/
	$(RM) -r services/*/supervise
	$(RM) twisted/plugins/dropin.cache

harness: bin/maas dev-db
	bin/maas shell --settings=maas.demo

syncdb: bin/maas dev-db
	bin/maas syncdb --noinput
	bin/maas migrate maasserver --noinput
	bin/maas migrate metadataserver --noinput

services := web pserv reloader txlongpoll
services := $(patsubst %,services/%/,$(services))

# The services/*/@something targets below are phony - they will never
# correspond to an existing file - but we want them to be evaluated
# for building, hence they are not added as .PHONY.

start: $(addsuffix @start,$(services))

stop: $(addsuffix @stop,$(services))

run:
	@utilities/run

status: $(addsuffix @status,$(services))

shutdown: $(addsuffix @shutdown,$(services))

services/%/@supervise: services/%/@deps
	@mkdir -p logs/$*
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

services/web/@deps: bin/maas dev-db

services/pserv/@deps: bin/twistd.pserv

services/reloader/@deps:

services/txlongpoll/@deps: bin/twistd.txlongpoll

.PHONY: \
    build check clean dev-db distclean doc \
    harness lint run shutdown syncdb test \
    sampledata start stop status
