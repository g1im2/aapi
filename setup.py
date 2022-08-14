from setuptools import setup

setup(
    name='pyapi',
    version='v0.1',
    packages=['aapi', 'eolinker'],
    url='',
    license='',
    author='smith',
    author_email='fxfpro@163.com',
    description='make request with json',

    install_requires=[
        'aiohttp'
    ],

    entry_points={
        'console_scripts': [
            'akt = aapi.do:main'
        ]
    }
)
