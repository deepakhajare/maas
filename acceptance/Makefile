include /etc/lsb-release

packaging := lp:~maas-maintainers/maas/packaging

# Special-case Precise.
ifeq ($(DISTRIB_CODENAME),precise)
packaging := $(packaging).precise
endif

upstream := $(abspath ..)
packages = $(abspath $(wildcard *.deb))
container := maas-$(DISTRIB_CODENAME)
containerdir := /var/lib/lxc/$(container)

## Convenience definitions.

define ephexec
sudo LC_ALL=C SSH_ASKPASS=$(abspath ubuntupass) setsid \
    lxc-start-ephemeral -b $(abspath .) -o $(container) -u ubuntu -- \
    DEBIAN_FRONTEND=noninteractive SUDO_ASKPASS=$(abspath ubuntupass)
endef

define ephexec-make
$(ephexec) $(abspath with-make) make -C $(abspath .)
endef

define check-service
test $(2) = $(wordlist 2,2,$(shell service $(1) status))  # $(1)
endef

## Top-level targets.

test: services sudo container build
	$(ephexec-make) $@-inner

# lxc-start-ephemeral does not return the exit code of any command it
# runs, so we delete any existing packages before building and check
# for their presence afterwards instead.
build: services sudo container source source/debian
	@$(RM) $(packages)
	$(ephexec-make) $@-inner
	@set -- $(packages) && test $$# -gt 0

container: $(containerdir)

services:
	$(call check-service,lxc,start/running)
	$(call check-service,lxc-net,start/running)

define phony-outer-targets
  build
  container
  services
  test
endef

## Targets that run within an LXC container.

test-inner: upgrade-inner
	sudo -AE dpkg --install -- $(packages)
	sudo -AE apt-get --fix-broken --assume-yes install

define build-packages
  debhelper
  devscripts
  dh-apport
endef

build-inner: #upgrade-inner
	sudo -AE apt-get --assume-yes install $(strip $(build-packages))
	cd source && debuild -i -us -uc -b

upgrade-inner:
	sudo -AE apt-get --assume-yes update
	sudo -AE apt-get --assume-yes upgrade

define phony-inner-targets
  build-inner
  test-inner
  upgrade-inner
endef

## Dependencies.

source:
	bzr export --uncommitted $@ $(upstream)

source/debian: | source
	bzr export $@ $(packaging)/debian

$(containerdir): | sudo
	sudo lxc-create -n $(container) -t ubuntu

## Miscellaneous.

sudo:
	@sudo -v

clean:
	$(RM) -r source *.build *.changes *.deb

define phony-misc-targets
  clean
  sudo
endef

## Phony.

define phony
  $(phony-inner-targets)
  $(phony-misc-targets)
  $(phony-outer-targets)
endef

phony := $(sort $(strip $(phony)))

.PHONY: $(phony)
