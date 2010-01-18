from setuptools import find_packages, setup

version='0.1'

setup(
	name='Trac2mite', 
	version=version,
	description="Trac2mite connects your Trac account with your mite.account. Track your time easily on issues within Trac (requires 'TracHoursPlugin') and get them automatically send to mite.",
	packages=find_packages(exclude=['*.tests*']),
	author="Yolk - Sebastian Munz & Julia Soergel GbR / Thomas Klein",
	author_email='thomas.klein83@gmail.com',
	url="http://github.com/thomasklein/Trac2mite",
	keywords="trac plugin mite yolk",
	license="MIT License",
	install_requires=['TracHoursPlugin'],
	dependency_links=['http://trac-hacks.org/svn/trachoursplugin/0.11'],
	include_package_data=True,
	package_data={'trac2mite': ['templates/*.html', 
								'htdocs/css/*.css',
								'htdocs/js/*.js', 
								'htdocs/images/*']},
	entry_points = """
	[trac.plugins]
	trac2mite.trac2mite = trac2mite.trac2mite
	trac2mite.setup = trac2mite.setup
	trac2mite.userprefs = trac2mite.userprefs
	trac2mite.web_ui = trac2mite.web_ui
	"""
)