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

lint-css: sources = src/maasserver/static/css
lint-css: /usr/bin/pocketlint
	@find $(sources) -type f \
	    -print0 | xargs -r0 pocketlint --max-length=120

lint-js: sources = src/maasserver/static/js
lint-js: /usr/bin/pocketlint
	@find $(sources) -type f -print0 | xargs -r0 pocketlint

/usr/bin/pocketlint:
	sudo apt-get install python-pocket-lint

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

define phony_targets
  build
  check
  clean
  dev-db
  distclean
  doc
  harness
  lint
  lint-css
  lint-js
  sampledata
  syncdb
  test
endef

#
# Development services.
#

services := web pserv reloader txlongpoll
services := $(patsubst %,services/%/,$(services))

run:
	@utilities/run

start: $(addsuffix @start,$(services))

stop: $(addsuffix @stop,$(services))

status: $(addsuffix @status,$(services))

shutdown: $(addsuffix @shutdown,$(services))

supervise: $(addsuffix @supervise,$(services))

define phony_services_targets
  run
  shutdown
  start
  status
  stop
  supervise
endef

# Pseudo-magic targets for controlling individual services.

services/%/@run: services/%/@stop services/%/@deps
	cd services/$* && ./run

services/%/@supervise: services/%/@deps
	@mkdir -p logs/$*
	@touch $(@D)/down
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

# Dependencies for individual services.

services/web/@deps: bin/maas dev-db

services/pserv/@deps: bin/twistd.pserv

services/reloader/@deps: services/web/@supervise services/pserv/@supervise

services/txlongpoll/@deps: bin/twistd.txlongpoll

#
# Phony stuff.
#

define phony
  $(phony_services_targets)
  $(phony_targets)
endef

phony := $(sort $(strip $(phony)))

.PHONY: $(phony)
