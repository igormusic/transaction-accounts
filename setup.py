from setuptools import setup, find_packages

setup(
    name='transaction-accounts',
    version='0.0.1',
    description='Create configuration for transactional accounts and implement account runtime',
    author='Igor Music',
    author_email='igormusich@gmail.com',
    packages=find_packages(),
    install_requires=[
        'python-dateutil',
        'dataclasses-json'
    ],
    entry_points={
    }
)
