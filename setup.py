from setuptools import setup
from setuptools import find_packages


version = '1.0.1'

install_requires = [
    'setuptools',

    'certbot>=0.21.1',
    'zope.interface',

    'requests',
    'lxml',
    'six',
    'bs4',
]

with open('README.rst') as in_file:
    long_description = in_file.read()

setup(
    name='certbot-dns-hurricane-electric',
    version=version,
    description='Hurricane Electric DNS Authenticator plugin for Certbot',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/studioeng/certbot-dns-hurricane-electric',
    author='Studioeng',
    author_email='byattsystems@gmail.com',
    license='MIT',
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',
    classifiers=[
        'Environment :: Plugins',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Security',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Networking',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],
    keywords='certbot dns hurricane-electric dns-01 authenticator api',

    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    entry_points={
        'certbot.plugins': [
            'dns-hurricane_electric = certbot_dns_hurricane_electric.dns_hurricane_electric:Authenticator',
        ],
    }
)
