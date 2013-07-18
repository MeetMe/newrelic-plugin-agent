import os
from distutils import sysconfig

# Check to see if the previous version was installed and clean up
# installed-files.txt
prune = ['var/', 'var/run/', 'var/log/']
python_lib_dir = sysconfig.get_python_lib()
fixed = False
for dir_path, dir_names, file_names in os.walk(python_lib_dir):
    for dir_name in dir_names:
        if dir_name[:21] == 'newrelic_plugin_agent' and \
                        dir_name[-8:] == 'egg-info':
            filename = '%s/%s/installed-files.txt' % (python_lib_dir, dir_name)
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
            with open(filename, 'w') as handle:
                handle.write('\n'.join(output))
            break
    break
if fixed:
    print 'Fixed a serious uninstallation problem in previous version'
