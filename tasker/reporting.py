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

import Queue
import logging

class Reports(object):
    """Instances of this class are used as reporting mechanism by which the
    plugins can comminucate back to whatever frontend we are using.

    Message has four parts:
    origin - who sent the message (name of the plugin, Pluginsystem, ...)
    semantics - what level does the message describe (system, plugin, task, ..)
    importance - how is that message important (debug, info, error, ...)
                 this must be number, possibly the same as in logging module
    message - the message itself
    """

    def __init__(self, maxsize=-1):
        self._queue = Queue.Queue(maxsize = maxsize)

    def put(self, message, origin, semantics, importance = logging.INFO):
        return self._queue.put((origin, semantics, importance, message))

    def get(self, *args, **kwargs):
        return self._queue.get(*args, **kwargs)


    #There will be helper methods inspired by logging module
    def error(self, message, origin, semantics):
        return self.put(message, origin, semantics, importance = logging.ERROR)

