import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

import re
vdir = __file__[0:__file__.rfind('/')]+'/' if __file__.rfind('/')>=0 else ''
VERSIONFILE = vdir+'k8sredis/__init__.py'
with open(VERSIONFILE, 'rt') as vfile:
   verstrline = vfile.read()
   VSRE = r"^__version__[ ]*=[ ]*['\"]([^'\"]*)['\"]"
   mo = re.search(VSRE, verstrline, re.M)
   if mo:
      version_info = mo.group(1)
   else:
      raise RuntimeError("Unable to find version string in %s." % (VERSIONFILE,))

setuptools.setup(
    name="k8sredis",
    version=version_info,
    author='Alex Miłowski',
    author_email='alex@milowski.com',
    description='A module for redis kubectl plugins and automation',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/alexmilowski/redis-k8s-scratch/kubectl-plugins',
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords='redis k8s kubernetes',
    python_requires='>=3.6',
    install_requires=['kubernetes pyyaml']
)
