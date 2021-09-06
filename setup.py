# Copyright 20.35 Nitor Creations Oy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
from setuptools import setup
from ec2_utils import CONSOLESCRIPTS

if sys.version_info[0] == 2:
    python2_or_3_test_deps = ['pytest==4.6.11', 'pytest-mock==1.13.0', 'mock==3.0.5']
elif sys.version_info[0] == 3:
    python2_or_3_test_deps = ['pytest-mock', 'mock']
    python2_or_3_test_deps.insert(0, "pytest")

setup(name='ec2-utils',
      version='0.35',
      description='Tools for using on an ec2 instance',
      url='http://github.com/NitorCreations/ec2-utils',
      download_url='https://github.com/NitorCreations/ec2-utils/tarball/0.35',
      author='Pasi Niemi',
      author_email='pasi@nitor.com',
      license='Apache 2.0',
      packages=['ec2_utils'],
      include_package_data=True,
      entry_points={
          'console_scripts': CONSOLESCRIPTS,
      },
      install_requires=[
          'future',
          'threadlocal-aws>=0.10',
          'awscli',
          'requests',
          'termcolor',
          'argcomplete',
          'python-dateutil',
          'retry',
          'netifaces',
          'jmespath'
      ] + ([
          'win-unicode-console',
          'wmi',
          'pypiwin32'
          ] if sys.platform.startswith('win') else []),
      tests_require=[
          'pytest-cov',
          'coverage',
          'coveralls'
      ] + python2_or_3_test_deps,
      zip_safe=False)
