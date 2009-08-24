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

import logging
import unittest
import warnings

import atfork
import atfork.stdlib_fixer


class atfork_stdlib_fixer_test(unittest.TestCase):
    def test_fix_logging_module(self):
        # Test that it issues the already imported warning.
        warnings.filterwarnings('error', '.*module already imported.*')
        self.assertRaises(UserWarning, atfork.stdlib_fixer.fix_logging_module)

        # Now let it run, ignoring rather than raising the warning.
        warnings.filterwarnings('ignore', '.*module already imported.*')
        atfork.stdlib_fixer.fix_logging_module()
        self.assertTrue(logging.fixed_for_atfork)

        # Test that the fixup is never installed twice.
        old_acquire_lock = logging._acquireLock
        try:
            logging._acquireLock = lambda: self.fail('fixup ran a second time')
        finally:
            logging._acquireLock = old_acquire_lock
        atfork.stdlib_fixer.fix_logging_module()

        orig_atfork = atfork.atfork
        logging_handler_atfork_calls = []

        def fake_atfork(prepare, parent, child):
            logging_handler_atfork_calls.append((prepare, parent, child))

        atfork.atfork = fake_atfork
        try:
            handler = logging.Handler(level=logging.DEBUG)
        finally:
            atfork.atfork = orig_atfork
        self.assertEqual([(handler.lock.acquire,
                           handler.lock.release, handler.lock.release)],
                         logging_handler_atfork_calls)


if __name__ == '__main__':
    unittest.main()
