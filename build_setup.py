#
# Copyright (c) 2015-2018 Canonical, Ltd.
#
# This file is part of Talisker
# (see http://github.com/canonical-ols/talisker).
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
import collections
from setuptools.config import read_configuration

config = read_configuration('setup.cfg')
data = {}
collections.OrderedDict()
data.update(config['metadata'])
data.update(config['options'])
data['long_description'] = 'DESCRIPTION'

long_description = open('README.rst').read().strip()
sorted_data = collections.OrderedDict((k, data[k]) for k in sorted(data))


def print_line(k, v, indent='    '):
    if isinstance(v, list):
        print('{}{}=['.format(indent, k))
        for i in v:
            print("{}    '{}',".format(indent, i))
        print('{}],'.format(indent))
    elif isinstance(v, dict):
        print('{}{}=dict('.format(indent, k))
        for k2 in sorted(v):
            print_line(k2, v[k2], indent + '    ')
        print('{}),'.format(indent))
    elif isinstance(v, bool):
        print("{}{}={},".format(indent, k, v))
    elif k == 'long_description':
        print("{}{}={},".format(indent, k, v))
    else:
        print("{}{}='{}',".format(indent, k, v))


print("""#!/usr/bin/env python
#
# Copyright (c) 2015-2018 Canonical, Ltd.
#
# This file is part of Talisker
# (see http://github.com/canonical-ols/talisker).
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
#
# Note: this file is autogenerated from setup.cfg for older setuptools
#
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

DESCRIPTION = '''
{}
'''

setup(""".format(long_description))

for k, v in sorted_data.items():
    print_line(k, v)

print(')')
