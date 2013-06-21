from setuptools import setup
import os
from os import path

base_path = '/opt/newrelic_plugin_agent'
data_files = dict()
data_files[base_path] = ['README.md']

# etc dir
for dir_path, dir_names, file_names in os.walk('etc'):
    install_path = '%s/%s' % (base_path, dir_path)
    if install_path not in data_files:
        data_files[install_path] = list()
    for file_name in file_names:
        data_files[install_path].append('%s/%s' % (dir_path, file_name))

# var dir
for dir_path, dir_names, file_names in os.walk('var'):
    install_path = '/%s' % dir_path
    if dir_path not in data_files:
        data_files[install_path] = list()
    for file_name in file_names:
        data_files[install_path].append('%s/%s' % (dir_path, file_name))

with open('MANIFEST.in', 'w') as handle:
    for path in data_files:
        for filename in data_files[path]:
            handle.write('include %s\n' % filename)

console_scripts = ['newrelic_plugin_agent=newrelic_plugin_agent.agent:main']
install_requires = ['clihelper>=1.7.0', 'requests']
tests_require = []
extras_require = {'mongodb': ['pymongo'],
                  'pgbouncer': ['psycopg2'],
                  'postgresql': ['psycopg2']}

setup(name='newrelic_plugin_agent',
      version='1.0.12',
      description='Python based agent for collecting metrics for NewRelic',
      url='https://github.com/MeetMe/newrelic_plugin_agent',
      packages=['newrelic_plugin_agent', 'newrelic_plugin_agent.plugins'],
      author='Gavin M. Roy',
      author_email='gmr@meetme.com',
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
