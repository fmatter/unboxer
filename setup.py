from setuptools import setup, find_packages


setup(
    name="box2csv",
    version="0.0.1",
    author='Florian Matter',
    author_email='florianmatter@gmail.com',
    description='Convert shoe- and toolbox databases to CLDF-ready CSV files',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    license="GNU GPLv3",
    url='https://github.com/fmatter/box2csv',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [],
    },
    platforms='any',
    python_requires='>=3.6',
    install_requires=[],
    # extras_require={},
)
