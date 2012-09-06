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
	    SUDO_ASKPASS=$(abspath ubuntupass) $(abspath test) $(packages)

build: source source/debian
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
