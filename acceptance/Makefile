packaging := lp:~maas-maintainers/maas/packaging
upstream := $(abspath $(PWD)/..)

##

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

.PHONY: build clean install-missing-packages
