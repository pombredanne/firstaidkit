from setuptools import setup

setup(name='firstaidkit',
      version='0.1.0',
      description='System Rescue Tool',
      author='Martin Sivak / Joel Andres Granados',
      author_email='msivak@redhat.com / jgranado@redhat.com',
      url='http://fedorahosted.org/firstaidkit',
      license='GPLv2',
      packages = ['pyfirstaidkit'],
      scripts = ['firstaidkit']
      )
