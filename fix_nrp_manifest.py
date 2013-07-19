import os
from os import path
import site

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
