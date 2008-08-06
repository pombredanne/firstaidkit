# First Aid Kit - diagnostic and repair tool for Linux
# Copyright (C) 2008 Joel Andres Granados <jgranado@redhat.com>
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

import pyfirstaidkit.utils as utils

import os.path
import re
import subprocess
import tempfile

import minihal
import parted

# List of known or expected values for the system.
#
# Where the grub dir shoulc be with respect to the partition root.
locations = ["/boot/grub", "/grub"]

# The files that are expected to make grub work. nfiles -> needed files.
nfiles = ["stage1", "stage2"]

# Expected grub configuration file name.
conffile = "grub.conf"

# Expected mounts file
mounts = "/proc/mounts"

# Disks starting with these strings will be ignored when looking for system
# storage devices.
ignore_devs = ["sr"]

def get_all_devs():
    """Get all the storage devices that exists currently on the system.

    We only want the device name and the partitions for each device.
    We don't want the parted structures.
    Return - dictionary with device name and all device partitions.
    """

    # Must use an inner function as the test does not consider the device
    # number.  Olny device type.
    def is_dev_in_ignored(dev):
        for ignored in ignore_devs:
            if dev["device"].replace("/dev/","").startswith(ignored):
                return True
        return False

    retval = {}
    for device in minihal.get_devices_by_type("storage"):
        if device is None:
            continue

        elif is_dev_in_ignored(device):
            continue

        elif "storage.removable.media_available" in device.keys() and \
                device["storage.removable.media_available"] == False:
            # We ignore stuff that has no media inserted.
            continue

        else:
            # parted will provide us with all the partitions.
            partitions = []
            parteddev = parted.PedDevice.get(device["device"])
            disk = parted.PedDisk.new(parteddev)
            part = disk.next_partition()
            while part:
                if part.num > 0:
                    partitions.append(
                            Dname("%s%s"%(device["device"],part.num)))
                part = disk.next_partition(part)
            # The key will be the device name and it will contain a list of
            # parts.
            retval[Dname.asName(device["device"])] = partitions

    return retval

def grub_dir_in_partition(part):
    """Search for the grub directory and all needed files in the partition

    It will search for the known locations and necessary files for in the
    specified partition.
    Return - list containing partitions with grub.
    """
    def do_unmount():
        part_unmount(part)
        if os.path.isdir(mountpoint):
            os.rmdir(mountpoint)


    # We search to see if the partition is mounted.  If its not we must
    # mount it in a temporary place to unmount it before we leave this
    # function.
    unmount=False
    mountpoint = is_part_mounted(part)
    if len(mountpoint) == 0:
        # This means that its not mounted. And we must unmount it at the
        # end.
        unmount=True

        # Select a safe temporary directory where to mount it.
        mountpoint = tempfile.mkdtemp(prefix=part.name())

        # If the mount fails it will raise an excpetion.  We must catch the
        # exception when this function is called.  Same goes for part_unmount.
        try:
            part_mount(part, mountpoint)
        except:
            # The partition was not mounted erase the directory if empty.
            # leave if the directoy is not empty
            os.rmdir(mountpoint)
            return False

    # Search for the grub directorie in the mounted partition.
    grubdir=""
    for dir in locations:
        if os.path.isdir(utils.join(mountpoint, dir)):
            grubdir=utils.join(mountpoint, dir)
            # We don't care if there is another directory in the same partition
            # It is very unlikely and not an intelligent thing to do anyway.
            break

    # At this point if we didn't find any of the locations, then grub is not
    # in this partition.
    if len(grubdir) == 0:
        if unmount:
            do_unmount()
        return False

    # Now we have to search for the files in the grub directory.  The list in
    # nfiles is the needed files.  So if one of the files is not found we
    # consider that there is not enough context to fix the issue in this part.
    # FIXME add some code that can replace the files that are missing.
    foundfiles = 0
    for file in nfiles:
        if os.path.isfile(utils.join(grubdir, file)):
            foundfiles = foundfiles + 1

    # If we don't have all the files we will not even consider this partition.
    if len(nfiles) > foundfiles:
        if unmount:
            do_unmount()
        return False

    # Search for the grub config file.
    if not os.path.isfile(utils.join(grubdir, conffile)):
        if unmount:
            do_unmount
        return False

    # FIXME need to implement the kernel and initrd image searching code.
    # for now we trust that the images are actually there.

    if unmount:
        do_unmount()

    return True

def is_part_mounted(part):
    """Search /proc/mounts for the presence of the partition.

    It searches for the "/dev/something" device.
    If its not mounted it returns an empty mountpoint (not mounted).
    If its mounted it returns the mount point.
    """
    for line in file(mounts).readlines():
        if re.search(part.path(), line) != None:
            # The mountpoint is in the second possition.
            return line.split(" ")[1]

    return ""

def part_mount(part, mountPoint, opts=None):
    """Mount the partition at mountpoint"""
    # Create the call
    call = ["mount"]
    if opts:
        call.append(opts)
    call.extend([part.path(), mountPoint])

    # Call mount
    proc = subprocess.Popen(call, stdout=subprocess.PIPE, \
            stderr=subprocess.PIPE)
    (out, err) = proc.communicate()
    retcode = proc.wait()
    if retcode != 0 or len(err) > 0:
        # The mount failed
        raise Exception("%s" % (part.path(), err))
    else:
        # This probably means that the mount succeded.
        return True

def part_unmount(part, opts=None):
    """Unmount the partition that is mounted at mountPoint

    part - It can actually be the part path or the mountpoint
    """

    # If its not a dev path its a mountpoint.
    if part.__class__.__name__ == "Dname":
        umountarg = part.path()
    else:
        umountarg = part

    # Create the call
    call = ["umount"]
    if opts:
        call.append(opts)
    call.append(umountarg)

    # Call umount
    proc = subprocess.Popen(call, stdout=subprocess.PIPE, \
            stderr=subprocess.PIPE)
    (out, err) = proc.communicate()
    retcode = proc.wait()
    if retcode != 0 or len(err) > 0:
        raise Exception("There was an error unmounting partition %s. " \
                "Error: %s." % (part.path(), err))
    else:
        return True

# The Strings contained in the grub stage one:
stage1strings = ["GRUB", "Geom", "Hard", "Disk", "Read", "Error"]

def grub_bin_in_dev(dev):
    """Will look in the first 446 bytes of the device for traces of grub.

    Will look for the strings that come with the grub stage1 image.  The
    strings are: "GRUB", "Geom", "Hard", "Disk", "Read" and "Error".  These
    strings must be compared considering the letter case.
    dev - Dname object representing the storage device.
    """
    if (os.path.exists(dev.path())):

        # Read the first 446 bytes of the dev.
        fd = os.open(dev.path(), os.O_RDONLY)
        first446b = os.read(fd, 446)
        os.close(fd)

        # Search for all the strings
        foundstrings = 0
        for string in stage1strings:
            if re.search(string, first446b) != None:
                foundstrings = foundstrings + 1

        # Only if all the strings are present we give the goahead.
        if foundstrings == len(stage1strings):
            return True

    return False


def grub_bin_in_part(part):
    """Will look in the first 446 bytes of the partition for traces of grub.

    Same conditions apply as in grub_bin_in_dev.
    """
    return grub_bin_in_dev(part)

# Input string for the grub batch mode.
# FIXME: Do we need lba, stage2 specification, prefix?
batch_grub_install = """
root (%s)
setup (%s)
quit
"""
def install_grub(root, setup):
    """Install stage1 grub image in the specified place.

    root -  the root where the dir is.  This can be a divice or partition.
            It must be a Dname
    setup - the dev where to install image. This can be device or partition.
            It must be a Dname

    return - whatever the grub console puts on stdout.
    """

    # Construct the root string.
    grubroot = root.grubName()
    grubsetup = setup.grubName()

    # Run the command that installs the grub.
    # FIXME: We are not taking into account the device map.
    command = ["grub", "--batch"]
    proc = subprocess.Popen(command, stdout = subprocess.PIPE,
            stdin = subprocess.PIPE, stderr = subprocess.PIPE)
    (out, err) =  proc.communicate(batch_grub_install%(grubroot, grubsetup))

    m = re.search("Error.*\\n", "%s%s"%(out,err))
    if m != None:
        # raise an exception when grub shell returned an error.
        raise Exception("There was an error while installing grub. Error %s " \
                % m.group(0))

    return out

# I really don't like the fact that you can have a variable that represents
# a device or partition and not know, until runtime, with total certainty,
# if its "/dev/something" or just "something".

# The constant to transform a device leter to a grub hd number. ciconst
# (char int constant)
ciconst = ord('a')
class Dname:
    """Class to represent device names.

    It will only represent device and partitiosn.
    """
    # FIXME: extend this class to raid.
    def __init__(self, name):
        if name.__class__.__name__ == "Dname":
            self.dname = name.dname
        elif name.startswith("/dev/"):
            self.dname = name[5:]
        else:
            self.dname = name

    @classmethod
    def asPath(self, dev):
        """return the device in the "/dev/somthing" form."""
        if dev.__class__.__name__ == "Dname":
            return dev.path()
        else:
            temp = Dname(dev)
            return temp.path()

    @classmethod
    def asName(self, dev):
        """return the device in the "somthing" form"""
        if dev.__class__.__name__ == "Dname":
            return dev.name()
        else:
            temp = Dname(dev)
            return temp.name()

    @classmethod
    def asGrubName(self, dev, parenthesis = False):
        """return something that grub understands."""
        if dev.__class__.__name__ == "Dname":
            return dev.grubName(parenthesis)
        else:
            temp = Dname(dev)
            return temp.grubName(parenthesis)

    def path(self):
        return utils.join("/dev/", self.dname)

    def name(self):
        return self.dname

    def grubName(self, parenthesis = False):
        """Change the kernel device name to something that grub understands

        It returns a string of the form hd[devicd],[partition]
        """

        # First we search for the number that ends the device string.
        m = re.search("[0-9]+$", self.dname)
        if m == None:
            partnum = None
            devnum = ord(self.dname[len(self.dname)-1]) - ciconst
        else:
            # The grub partition number scheme is a little different.  Its safe
            # to assume that its one less than the usual scheme.
            partnum = int(m.group(0))
            temp = self.dname.strip(str(partnum))

            # Follow grub scheme
            partnum = partnum - 1

            # We now get the letter that is before the number
            devnum = ord(temp[len(temp)-1]) - ciconst

        # Must check to see if the values are in range.
        if (partnum != None and partnum < 0) or (devnum < 0):
            raise Exception("The conversion from kernel device scheme to " \
                    "grub scheme failed.")

        # Decide weather to return with or withoug parenthesis.
        if parenthesis:
            openpar = "("
            closepar = ")"
        else:
            openpar = ""
            closepar = ""

        # Create the gurb device string.
        if partnum == None:
            return "%shd%s%s"%(openpar, devnum, closepar)
        else:
            return "%shd%s,%s%s"%(openpar, devnum, partnum, closepar)

