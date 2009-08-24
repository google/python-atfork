#!/usr/bin/python
#
# Copyright 2009 Google Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# Licensed to the PSF under a Contributor Agreement.
#
# Author: Gregory P. Smith <greg@krypto.org>

import sys, os
top_dir = os.path.dirname(__file__)
os.environ['PYTHONPATH'] = top_dir

status = 0
test_dir = os.path.join(top_dir, 'atfork', 'tests')
for test_file in os.listdir(test_dir):
    if not test_file.endswith('.py'):
        continue
    test_path = os.path.join(test_dir,test_file)
    test_command = "'%s' '%s'" % (sys.executable, test_path)
    print 'Running', test_command
    status += os.system(test_command)

if status:
    sys.exit(1)
sys.exit(0)
