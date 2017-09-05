from setuptools import setup

setup(
    name='deromanize',
    version='0.4',
    author='FID-Judaica, Goethe Universität',
    license='MLP 2.0/EUPL 1.1',
    author_email='a.christianson@ub.uni-frankfurt.de',
    url='https://github.com/FID-Judaica/deromanize.py',
    description='rule-based algorithms converting Romanized text to original '
                'scripts',
    long_description=open('README.rst').read(),
    packages=['deromanize'],
)
