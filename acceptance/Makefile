include /etc/lsb-release

ifeq ($(DISTRIB_CODENAME),precise)
packaging := lp:~maas-maintainers/maas/packaging.precise
else ifeq ($(DISTRIB_CODENAME),quantal)
packaging := lp:~maas-maintainers/maas/packaging
else
$(error Release $(DISTRIB_CODENAME) not recognised)
endif

upstream := $(abspath ..)
packages = $(abspath $(wildcard *.deb))

##

test: build
	sudo LC_ALL=C SSH_ASKPASS=$(abspath ubuntupass) setsid \
	    lxc-start-ephemeral -b $(abspath .) -o maas-precise -u ubuntu -- \
	    SUDO_ASKPASS=$(abspath ubuntupass) $(abspath test) $(packages)

build: source source/debian
	cd source && debuild -i -us -uc -b

##

source:
	bzr export --uncommitted $@ $(upstream)

source/debian: | source
	bzr export $@ $(packaging)/debian

##

install-missing-packages:
	sudo apt-get install dh-apport

clean:
	$(RM) -r source *.build *.changes *.deb

##

define phony
  build
  clean
  install-missing-packages
  test
endef

phony := $(sort $(strip $(phony)))

.PHONY: $(phony)
