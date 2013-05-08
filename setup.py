from distutils.core import setup

install_requires = ['clihelper>=1.7.0', 'requests']
tests_require = []

setup(name='newrelic_plugin_agent',
      version='1.0.0',
      description='Base agent class for writing NewRelic Plugin Agents',
      url='https://github.com/MeetMe/newrelic_plugin_agent',
      py_modules=['newrelic_plugin_agent'],
      author='Gavin M. Roy',
      author_email='gmr@meetme.com',
      license='BSD',
      install_requires=install_requires,
      tests_require=tests_require)
