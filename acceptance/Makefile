include /etc/lsb-release

packaging := lp:~maas-maintainers/maas/packaging

# Special-case Precise.
ifeq ($(DISTRIB_CODENAME),precise)
packaging := $(packaging).precise
endif

upstream := $(abspath ..)
packages = $(abspath $(wildcard *.deb))
image := maas-$(DISTRIB_CODENAME)

##

define ephexec
sudo LC_ALL=C SSH_ASKPASS=$(abspath ubuntupass) setsid \
    lxc-start-ephemeral -b $(abspath .) -o $(image) -u ubuntu -- \
    DEBIAN_FRONTEND=noninteractive SUDO_ASKPASS=$(abspath ubuntupass)
endef

define ephexec-make
$(ephexec) $(abspath with-make) make -C $(abspath .)
endef

##

test: services sudo build image
	$(ephexec-make) $@-inner

test-inner: upgrade-inner
	sudo -AE dpkg --install -- $(packages)
	sudo -AE apt-get --fix-broken --assume-yes install

build: services sudo source source/debian
	$(ephexec-make) $@-inner

build-inner: upgrade-inner
	sudo -AE apt-get --assume-yes install devscripts debhelper dh-apport
	cd source && debuild -i -us -uc -b

image: /var/lib/lxc/$(image)

lxc:
	@service $@ status

lxc-net:
	@service $@ status

services: lxc lxc-net

upgrade-inner:
	sudo -AE apt-get --assume-yes update
	sudo -AE apt-get --assume-yes upgrade

##

source:
	bzr export --uncommitted $@ $(upstream)

source/debian: | source
	bzr export $@ $(packaging)/debian

/var/lib/lxc/$(image):
	sudo lxc-create -n $(image) -t ubuntu

##

sudo:
	@sudo -v

clean:
	$(RM) -r source *.build *.changes *.deb

##

define phony
  build
  clean
  image
  lxc
  lxc-net
  services
  sudo
  test
endef

phony := $(sort $(strip $(phony)))

.PHONY: $(phony)
