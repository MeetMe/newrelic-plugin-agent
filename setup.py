from distutils.core import setup
import os

base_path = '/opt/newrelic_plugin_agent'

data_files = dict()
data_files[base_path] = ['README.md']
for data_path in ['etc']:
    for dir_path, dir_names, file_names in os.walk(data_path):
        install_path = '%s/%s' % (base_path, dir_path)
        if install_path not in data_files:
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

setup(name='newrelic_plugin_agent',
      version='1.0.0',
      description='Python based agent for collecting metrics for NewRelic',
      url='https://github.com/MeetMe/newrelic_plugin_agent',
      packages=['newrelic_plugin_agent', 'newrelic_plugin_agent.plugins'],
      author='Gavin M. Roy',
      author_email='gmr@meetme.com',
      license='BSD',
      entry_points={'console_scripts': console_scripts},
      install_requires=install_requires,
      tests_require=tests_require)
