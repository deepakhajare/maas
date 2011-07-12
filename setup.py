#!/usr/bin/python

import yaml
import Cheetah
import os
import sys
import copy
import pprint
import libvirt
from Cheetah.Template import Template

NODES_RANGE = range(1,4)

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
		self.network = syscfg['network']['name']

	def __repr__(self):
		return("== %s ==\n ip: %s\n mac: %s\n template: %s\n" %
		       (self.name, self.ipaddr, self.mac, self.template))

	@property
	def ipaddr(self):
		return("%s.%s" % (self.ip_pre, self.ipnum))

	@property
	def disk0(self):
		return("%s/%s-disk0.img" % (self.basedir, self.name))

	def dictInfo(self):
		ret = vars(self)
		# have to add the getters
		for prop in ( "ipaddr", "disk0" ):
			ret[prop] = getattr(self,prop)
		return ret

	def toLibVirtXml(self):
		return(Template(file=self.template, searchList=[self.dictInfo()]).respond())

	def cobblerRegister(self, connection, profile):
		pass
		
class Node(Domain):
	def _setcfg(self, cfg, num):
		cfg = cfg['nodes']
		self.name = "%s%02i" % (cfg['prefix'],num)
		self.mac = "%s:%02x" % (cfg['mac_pre'],num)
		self.ipnum = num + 100
		self.template = cfg['template']
		self.mem = cfg['mem']
		return

class System(Domain):
	def _setcfg(self, cfg, ident):
		cfg = cfg['systems'][ident]
		self.name = ident
		self.mac = cfg['mac']
		self.ipnum = cfg['ip']
		self.template = cfg['template']
		self.mem = cfg['mem']

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

def writeDomXmlFile(dom, outpre=""):
	fname="%s%s.xml" % (outpre, dom.name)
	output = open(fname,"w")
	output.write(dom.toLibVirtXml())
	output.close()
	return fname

def libvirt_setup(config):
	conn = libvirt.open("qemu:///system")
	netname = config['network']['name']
	if netname in conn.listDefinedNetworks() or netname in conn.listNetworks():
		net = conn.networkLookupByName(netname)
		if net.isActive():
			net.destroy()
		net.undefine()

	allsys = {}
	for system in config['systems']:
		d = System(config, system)
		allsys[d.name]=d.dictInfo()
	for num in NODES_RANGE:
		d = Node(config, num)
		allsys[d.name]=d.dictInfo()

	conn.networkDefineXML(Template(file=config['network']['template'],
	                      searchList=[config['network'],
                                      {'all_systems': allsys }]).respond())

	print "defined network %s " % netname

	cob = System(config, "cobbler")
	systems = [ cob ]

	for node in NODES_RANGE:
		systems.append(Node(config, node))

	defined_systems = conn.listDefinedDomains()
	for sys in systems:
		if sys.name in defined_systems:
			dom = conn.lookupByName(sys.name)
			if dom.isActive():
				dom.destroy()
			dom.undefine()
		conn.defineXML(sys.toLibVirtXml())
		print "defined domain %s" % sys.name

def cobbler_setup(config):
	cob = System(config, "cobbler")
	

def main():
	outpre = "libvirt-cobbler-"
	cfg_file = "settings.cfg"

	if len(sys.argv) == 1:
		print "Usage: setup.py action\n  action one of: libvirt-setup"
		sys.exit(1)

	config = yaml_loadf(cfg_file)

	if sys.argv[1] == "libvirt-setup":
		libvirt_setup(config)
		sys.exit(0)
	elif sys.argv[1] == "cobbler-setup":
		cobbler_setup(config)
		sys.exit(0)

if __name__ == '__main__':
	main()

# vi: ts=4 noexpandtab
