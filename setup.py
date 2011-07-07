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

def getIp(cfg,num):

def Class Domain():
	def __init__(syscfg, ident):
		self.ip_pre = syscfg['network']['ip_pre']
		self._getcfg(syscfg,ident)

	return("%s.%s" % (cfg['network']['ip_pre'], num))

def Class Node(Domain):
    @property
    def ipaddr(self):
        return(self._cfgval_get("password",None))

	def _getcfg(cfg, num)
		cfg = cfg['nodes']
		self.name = "%s%02s" % (cfg['prefix'],num)
		self.mac = "%s:%02x" % (cfg['mac_pre'],num)
		self.ipnum = ident
		return

def Class System(Domain):
	def _getcfg(cfg, ident)
		self.name = ident
		self.mac = "%s:%02x" % (cfg['mac
		cfg = cfg['systems'][ident])
		ret['name'] = ident

	@property
	def ipaddr(self):
		return(getIp(cfg,cfg['ipnum'])
		

def getDomain(syscfg,ident):
	try:
		int(ident)
		return(Node(syscfg,ident))
	except:
		return(System(syscfg,ident))
		
def getSysCfg(cfg,name):
	ncfg = cfg['systems'][name]
	ret = copy.copy(ncfg)
	ret['name'] = name
	ret['ipaddr'] = getIp(cfg,ncfg['ip'])
	ret['disk0'] = "%s.img" % name
	return(ret)

def getNodeCfg(cfg,num):
	ncfg = cfg['nodes']
	ret = copy.copy(ncfg)
	ret['name'] = "%s%02s" % (ncfg['prefix'],num)
	ret['mac'] = "%s:%02x" % (ncfg['mac_pre'],num)
	ret['ipnum'] = getIp(cfg,num)
	ret['ipaddr'] = getIp(cfg,num)
	return(ret)

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

def systemCfg(config, name):
	pass

def getNetworkCfg(config):
	pass


def main():

	cfg_file = "settings.cfg"
	if len(sys.argv) > 1:
		cfg_file = sys.argv[1]

	config = yaml_loadf(cfg_file)

	cob = getSysCfg(config,"cobbler")
	print "===== cob ====="
	pprint.pprint(cob)
	pprint.pprint(renderSysDom(config, cob))


if __name__ == '__main__':
	main()

# vi: ts=4 noexpandtab
