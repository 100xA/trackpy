from setuptools import setup, find_packages

setup(
    name="trackpy",
    version="0.1.0",
    packages=find_packages(),
    py_modules=['trackpy'],
    install_requires=[
        'click>=8.1.7',
        'rich>=13.7.0',
        'python-dateutil>=2.8.2',
        'tabulate>=0.9.0',
    ],
    entry_points={
        'console_scripts': [
            'trackpy=trackpy:cli',
        ],
    },
)
