import os
from os import path
from setuptools import setup
import site
import sys

# Check to see if the previous version was installed and clean up
# installed-files.txt
prune = ['var/', 'var/run/', 'var/log/']

package_directories = site.PREFIXES
if site.USER_SITE:
    package_directories.append(site.USER_SITE)

try:
    import newrelic_plugin_agent
except ImportError:
    newrelic_plugin_agent = None

if newrelic_plugin_agent:
    package_directories.append(path.abspath(path.dirname(newrelic_plugin_agent.__file__) + '/..'))
for package_dir in package_directories:
    print 'Checking %s for newrelic_plugin_agent installation manifest' % package_dir
    fixed = False
    for dir_path, dir_names, file_names in os.walk(package_dir):
        for dir_name in dir_names:
            if dir_name[:21] == 'newrelic_plugin_agent' and \
                            dir_name[-8:] == 'egg-info':
                filename = '%s/%s/installed-files.txt' % (package_dir, dir_name)
                with open(filename, 'r') as handle:
                    output = []
                    for line in handle:
                        safe = True
                        for dir_path in prune:
                            if line[-(len(dir_path) + 1):].strip() == dir_path:
                                safe = False
                                fixed = True
                                break
                        if safe:
                            output.append(line.strip())
                if fixed:
                    with open(filename, 'w') as handle:
                        handle.write('\n'.join(output))
                    break
        break

if fixed:
    print 'Fixed a serious uninstallation problem in previous version'
else:
    print 'Did not find the installed-files.txt manifest uninstallation issue'


base_path = '%s/opt/newrelic_plugin_agent' % os.getenv('VIRTUAL_ENV', '')
data_files = dict()
data_files[base_path] = ['LICENSE',
                         'README.md',
                         'etc/init.d/newrelic_plugin_agent.deb',
                         'etc/init.d/newrelic_plugin_agent.rhel',
                         'etc/newrelic/newrelic_plugin_agent.cfg',
                         'apc-nrp.php',
                         'fix_nrp_manifest.py']

console_scripts = ['newrelic_plugin_agent=newrelic_plugin_agent.agent:main']
install_requires = ['clihelper>=1.7.0', 'requests', 'dnspython']
tests_require = []
extras_require = {'mongodb': ['pymongo'],
                  'pgbouncer': ['psycopg2'],
                  'postgresql': ['psycopg2']}

if sys.version_info < (2, 7, 0):
    install_requires.append('importlib')


setup(name='newrelic_plugin_agent',
      version='1.1.0',
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
