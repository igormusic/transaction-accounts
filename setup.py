from setuptools import setup, find_packages

setup(
    name='transaction-accounts',
    version='0.0.1',
    description='Create configuration for transactional accounts and implement account runtime',
    author='Igor Music',
    author_email='igormusich@gmail.com',
    packages=find_packages(),
    license='MIT',
    url='https://github.com/igormusic/transaction-accounts',
    download_url='https://github.com/igormusic/transaction-accounts/archive/refs/tags/0.0.1.tar.gz',
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
