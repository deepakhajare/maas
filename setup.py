#!/usr/bin/python

import yaml
import Cheetah
import os
import sys
import copy
import pprint
from Cheetah.Template import Template

def yaml_loadf(fname):
	fp = open(fname)
	ret = yaml.load(fp)
	fp.close()
	return(ret)

class Domain:
	def __init__(self, syscfg, ident, basedir=None):
		self.ip_pre = syscfg['network']['ip_pre']
		if basedir == None:
			basedir = os.path.abspath(os.curdir)
		self.basedir = basedir
		self._setcfg(syscfg,ident)

	def __repr__(self):
		return("== %s ==\n ip: %s\n mac: %s\n template: %s\n" %
		       (self.name, self.ipaddr, self.mac, self.template))

	@property
	def ipaddr(self):
		return("%s.%s" % (self.ip_pre, self.ipnum))

	@property
	def disk0(self):
		return("%s/%s-disk0.img" % (self.basedir, self.name))
		
class Node(Domain):
	def _setcfg(self, cfg, num):
		cfg = cfg['nodes']
		self.name = "%s%02s" % (cfg['prefix'],num)
		self.mac = "%s:%02x" % (cfg['mac_pre'],num)
		self.ipnum = ident
		self.template = cfg['template']
		return

class System(Domain):
	def _setcfg(self, cfg, ident):
		cfg = cfg['systems'][ident]
		self.name = ident
		self.mac = cfg['mac']
		self.ipnum = cfg['ip']
		self.template = cfg['template']

def renderSysDom(config, syscfg, stype="node"):
	return(Template(file=syscfg['template'], searchList=[config, syscfg]).respond())

# cobbler:
#  ip: 2 # ip address must be in dhcp range
#  mac: 00:16:3e:3e:a9:1a
#  template: libvirt-system.tmpl
#  mem: 524288
#	
#nodes:
# prefix: node
# mac_pre: 00:16:3e:3e:aa
# mam: 256

def main():

	cfg_file = "settings.cfg"
	if len(sys.argv) > 1:
		cfg_file = sys.argv[1]

	config = yaml_loadf(cfg_file)

	cob = System(config, "cobbler")
	pprint.pprint(cob)


if __name__ == '__main__':
	main()

# vi: ts=4 noexpandtab
