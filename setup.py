from setuptools import setup

setup(
    name='pyobs-tis',
    version='0.9',
    author='Tim-Oliver Husser',
    author_email='thusser@uni-goettingen.de',
    description='pyobs module for TIS cameras',
    packages=['pyobs_tis'],
    install_requires=[
        'numpy',
        'astropy'
    ]
)
