packaging := lp:~maas-maintainers/maas/packaging

version = $(shell \
    dpkg-parsechangelog -lsource/debian/changelog | \
        sed -rne 's,^Version: ([^-]+).*,\1,p')

orig = maas_$(version).orig.tar.gz

upstream = $(abspath $(PWD)/..)

##

build: source source/debian source.tar.gz
	ln -sfn source.tar.gz $(orig)
	cd source && debuild -i -us -uc -b

##

source:
	bzr export --uncommitted $@ $(upstream)

source/debian: | source
	bzr export $@ $(packaging)/debian

source.tar.gz: | source
	tar -czf $@ --exclude source/debian source

##

install-missing-packages:
	sudo apt-get install dh-apport

clean:
	$(RM) -r build-area source packaging
	$(RM) *.orig.tar.gz *.debian.tar.gz source.tar.gz
	$(RM) *.build *.dsc *.changes *.deb

##

.PHONY: build clean install-missing-packages
