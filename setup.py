from setuptools import setup
from distutils import cmd
from distutils.command.install_data import install_data as _install_data
from distutils.command.build import build as _build

import os
import subprocess


class build_trans(cmd.Command):
    description = 'Compile .po files into .mo files'
    def initialize_options(self):
        pass
 
    def finalize_options(self):
        pass
 
    def run(self):
        po_dir = os.path.join(os.path.dirname(os.curdir), 'po')
        for path, names, filenames in os.walk(po_dir):
            for f in filenames:
                if f.endswith('.po'):
                    lang = f[:len(f) - 3]
                    src = os.path.join(path, f)
                    dest_path = os.path.join('build', 'locale', lang, 'LC_MESSAGES')
                    dest = os.path.join(dest_path, 'firstaidkit.mo')
                    if not os.path.exists(dest_path):
                        os.makedirs(dest_path)
                    if not os.path.exists(dest):
                        print 'Compiling %s' % src
                        #msgfmt.make(src, dest)
                        subprocess.Popen(['msgfmt.py', '-o', dest, src])
                    else:
                        src_mtime = os.stat(src)[8]
                        dest_mtime = os.stat(dest)[8]
                        if src_mtime > dest_mtime:
                            print 'Compiling %s' % src
                            #msgfmt.make(src, dest)
                            subprocess.Popen(['msgfmt.py', '-o', dest, src])

class build(_build):
    sub_commands = _build.sub_commands + [('build_trans', None)]
    def run(self):
        _build.run(self)

class install_data(_install_data):
    def run(self):
        for lang in os.listdir('build/locale/'):
            lang_dir = os.path.join('/usr/share/locale', lang, 'LC_MESSAGES')
            lang_file = os.path.join('build/locale', lang, 'LC_MESSAGES/firstaidkit.mo')
            self.data_files.append( (lang_dir, [lang_file]) )
        _install_data.run(self)

cmdclass = {
    'build': build,
    'build_trans': build_trans,
    'install_data': install_data,
}

setup(name='firstaidkit',
      version='0.2.11',
      description='System Rescue Tool',
      author='Martin Sivak / Joel Andres Granados',
      author_email='msivak@redhat.com / jgranado@redhat.com',
      url='http://fedorahosted.org/firstaidkit',
      license='GPLv2+',
      packages = ['pyfirstaidkit', 'pyfirstaidkit/utils'],
      scripts = ['firstaidkit', 'firstaidkitrevert', 'firstaidkit-qs'],
      data_files = [('', '')],
      cmdclass = cmdclass,
      )

