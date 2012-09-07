include /etc/lsb-release

packaging := lp:~maas-maintainers/maas/packaging.$(DISTRIB_CODENAME)

# Special-case Quantal.
ifeq ($(DISTRIB_CODENAME),quantal)
packaging := lp:~maas-maintainers/maas/packaging
endif

upstream := $(abspath ..)
packages = $(abspath $(wildcard *.deb))
image := maas-$(DISTRIB_CODENAME)

##

test: sudo build image
	sudo LC_ALL=C SSH_ASKPASS=$(abspath ubuntupass) setsid \
	    lxc-start-ephemeral -b $(abspath .) -o $(image) -u ubuntu -- \
	    SUDO_ASKPASS=$(abspath ubuntupass) $(abspath with-make) \
	    make -C $(abspath .) test-inner

test-inner:
	sudo -A dpkg --install -- $(packages)
	sudo -A apt-get --fix-broken --assume-yes install

build: sudo source source/debian
	sudo LC_ALL=C SSH_ASKPASS=$(abspath ubuntupass) setsid \
	    lxc-start-ephemeral -b $(abspath .) -o $(image) -u ubuntu -- \
	    SUDO_ASKPASS=$(abspath ubuntupass) $(abspath with-make) \
	    make -C $(abspath .) build-inner

build-inner:
	sudo -A apt-get --assume-yes install devscripts debhelper dh-apport
	cd source && debuild -i -us -uc -b

image:
ifeq ($(filter $(image),$(shell lxc-ls)),)
	sudo lxc-create -n $(image) -t ubuntu
endif

##

source:
	bzr export --uncommitted $@ $(upstream)

source/debian: | source
	bzr export $@ $(packaging)/debian

##

sudo:
	@sudo -v

install-missing-packages:
	sudo apt-get install dh-apport

clean:
	$(RM) -r source *.build *.changes *.deb

##

define phony
  build
  clean
  image
  install-missing-packages
  sudo
  test
endef

phony := $(sort $(strip $(phony)))

.PHONY: $(phony)
