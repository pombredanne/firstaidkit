# First Aid Kit - diagnostic and repair tool for Linux
# Copyright (C) 2007 Martin Sivak <msivak@redhat.com>
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import ConfigParser
import os
from cStringIO import StringIO
from shlex import shlex

if os.environ.has_key("FIRST_AID_KIT_CONF"):
    cfgfile = os.environ["FIRST_AID_KIT_CONF"].split(":")
else:
    cfgfile = ["/etc/firstaidkit/firstaidkit.conf", os.environ["HOME"]+"/.firstaidkit.conf"]


def createDefaultConfig(config):
    """Create the default config with the object."""
    config.operation.flags = ""
    config.operation.mode = ""
    config.operation.params = ""
    config.operation.help = "False"
    config.operation.gui = "console"
    config.operation.verbose = "False"
    config.operation.dependencies = "True"
    config.operation.interactive = "False"
    config.log.method = "file"
    config.log.filename = "/var/log/firstaidkit.log"
    config.plugin.disabled = ""
    config.backup.method = "file"
    config.backup.path = "/tmp/firstaidkitbackup"

    # Setup a sane default root directory.
    if os.path.isdir("/mnt/sysimage"):
        config.system.root = "/mnt/sysimage"
    else:
        config.system.root = "/"

    # Set the directory containing cfg bits for different services/packages
    config.system.configuration = "/etc/firstaidkit"

    # Frontend modules are in specified directories
    config.system.frontend = "'/usr/lib64/firstaidkit/frontend' '/usr/lib/firstaidkit/frontend'"

    #
    # There will be 4 default places where FAK will look for plugins,  these 4 names
    # will be reserved in the configuration.  lib{,64}-firstaidkit-{,examples}
    #
    config.add_section("paths")
    for dir in ["firstaidkit/plugins", "firstaidkit/plugins/examples"]:
        for root in [ "usr/lib64", "usr/lib"]:
            if os.path.exists( "/%s/%s" % (root,dir)):
                config.set( "paths",  "%s/%s"%(dir[5:], root),"/%s/%s" %(root, dir) )


class LockedError(Exception):
    pass

class FAKConfigSection(object):
    """Proxy object for one configuration section"""

    def __init__(self, cfg, name):
        self.__dict__["__section_name"] = name
        self.__dict__["__configuration"] = cfg

    def __getattr__(self, key):
        if not self.__dict__["__configuration"].has_section(self.__dict__["__section_name"]) and self.__dict__["__section_name"]!="DEFAULT":
            raise ConfigParser.NoSectionError(self.__dict__["__section_name"])

        if not self.__dict__["__configuration"].has_option(self.__dict__["__section_name"], key):
            raise ConfigParser.NoOptionError(key, self.__dict__["__section_name"])

        return self.__dict__["__configuration"].get(self.__dict__["__section_name"], key)

    def __setattr__(self, key, value):
        if self.__dict__["__configuration"].__dict__.has_key("_lock") and self.__dict__["__configuration"].__dict__["_lock"]:
            raise LockedError(key)

        if not self.__dict__["__configuration"].has_section(self.__dict__["__section_name"]) and self.__dict__["__section_name"]!="DEFAULT":
            self.__dict__["__configuration"].add_section(self.__dict__["__section_name"])
        self.__dict__["__configuration"].set(self.__dict__["__section_name"], key, value)

    def _list(self, key):
        l = []
        lex = shlex(instream = StringIO(getattr(self, key)), posix = True)
        token = lex.get_token()
        while token!=lex.eof:
            l.append(token)
            token = lex.get_token()
        return l

    def valueItems(self):
        """Usefull when you don't care about the name of the items."""
        if not self.__dict__["__configuration"].has_section(self.__dict__["__section_name"]) and self.__dict__["__section_name"]!="DEFAULT":
            raise ConfigParser.NoSectionError(self.__dict__["__section_name"])
        tmpList = self.__dict__["__configuration"].items(self.__dict__["__section_name"])
        retVal = []
        for element in tmpList:
            retVal.append(element[1])
        return retVal


class FAKConfigMixIn(object):
    """Enhance ConfigParser so we can use it in the python way (config.section.value)"""

    def __getattr__(self, section):
        return FAKConfigSection(self, section)

    def lock(self):
        self.__dict__["_lock"] = True

    def unlock(self):
        self.__dict__["_lock"] = False

class FAKConfig(ConfigParser.SafeConfigParser, FAKConfigMixIn):
    def getConfigBits(self, name):
        return getConfigBits(name, cfg = self)

Config = FAKConfig()
createDefaultConfig(Config)
Config.read(cfgfile)

def getConfigBits(name, cfg = Config):
    """returns configuration object loaded with bits from designated configuration file/service
    
       name - service you need info from
       cfg - configuration object containing the system.configuration value, to specify, where to look for the service file"""
    c = FAKConfig()
    c.read(os.path.join(cfg.system.configuration, name))
    c.lock()
    return c

