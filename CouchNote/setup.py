#from ez_setup import use_setuptools
#use_setuptools()
from setuptools import setup, find_packages

setup(name="CouchNote",
      version="0.1dev",
      description="CouchNote cmd line",
      author="Nick Fisher",
      packages = find_packages(),
      zip_safe = True,
      entry_points = {
          'console_scripts': [
              'couchnote = couchnote.tool:main',
          ]
      }
     )
