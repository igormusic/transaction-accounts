from setuptools import setup, find_packages

try:
    import pypandoc
    long_description = pypandoc.convert_file('README.md', 'rst')
except(IOError, ImportError):
    long_description = open('README.md').read()


setup(
    name='transaction-accounts',
    version='0.0.2',
    description='Create configuration for transactional accounts and implement account runtime',
    long_description=long_description,
    author='Igor Music',
    author_email='igormusich@gmail.com',
    packages=find_packages(),
    license='MIT',
    url='https://github.com/igormusic/transaction-accounts',
    download_url='https://github.com/igormusic/transaction-accounts/archive/refs/tags/0.0.2.tar.gz',
    keywords=['TRANSACTION PROCESSING', 'LOANS', 'SAVINGS', 'ACCOUNTS', 'FINANCE', 'BANKING'],
    install_requires=[
        'python-dateutil',
        'dataclasses-json'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',  # Define that your audience are developers
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.9',

    ],
)
