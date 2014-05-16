import os
from setuptools import setup
import sys

base_path = '%s/opt/newrelic-plugin-agent' % os.getenv('VIRTUAL_ENV', '')
data_files = dict()
data_files[base_path] = ['LICENSE',
                         'README.rst',
                         'etc/init.d/newrelic-plugin-agent.deb',
                         'etc/init.d/newrelic-plugin-agent.rhel',
                         'etc/newrelic/newrelic-plugin-agent.cfg',
                         'apc-nrp.php']

console_scripts = ['newrelic-plugin-agent=newrelic_plugin_agent.agent:main']
install_requires = ['helper>=2.2.2', 'requests>=2.0.0']
tests_require = []
extras_require = {'mongodb': ['pymongo'],
                  'pgbouncer': ['psycopg2'],
                  'postgresql': ['psycopg2']}

if sys.version_info < (2, 7, 0):
    install_requires.append('importlib')

setup(name='newrelic_plugin_agent',
      version='1.3.0',
      description='Python based agent for collecting metrics for NewRelic',
      url='https://github.com/gmr/newrelic-plugin-agent',
      packages=['newrelic_plugin_agent', 'newrelic_plugin_agent.plugins'],
      author='Gavin M. Roy',
      author_email='gavinmroy@gmail.com',
      license='BSD',
      entry_points={'console_scripts': console_scripts},
      data_files=[(key, data_files[key]) for key in data_files.keys()],
      install_requires=install_requires,
      extras_require=extras_require,
      tests_require=tests_require,
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: BSD License',
          'Operating System :: POSIX',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 2 :: Only',
          'Topic :: System :: Monitoring'])
