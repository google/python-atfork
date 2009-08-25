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

"""Tests for atfork."""

import os
import sys
from cStringIO import StringIO
import traceback
import unittest

import atfork


class AtforkTest(unittest.TestCase):
    def setUp(self):
        atfork.monkeypatch_os_fork_functions()
        self.calls = []
        self.orig_stderr = sys.stderr

        self.assertFalse(atfork._fork_lock.locked(),
                         "atfork._fork_lock not released by an earlier test!")

        # Unregister calls registered by earlier tests.
        atfork._prepare_call_list = []
        atfork._parent_call_list = []
        atfork._child_call_list = []


    def tearDown(self):
        # Un-monkeypatch the os module.  ook.
        global os
        os = reload(os)
        sys.stderr = self.orig_stderr


    def _pre(self):
        self.calls.append(self._pre)

    def _parent(self):
        self.calls.append(self._parent)


    def _child(self):
        self.calls.append(self._child)


    def _other(self):
        self.calls.append(self._other)


    def _raise_pre(self):
        self._pre()
        raise RuntimeError('This as the first parent error expected.')


    def _raise_parent(self):
        self._parent()
        raise RuntimeError('This as the second parent error expected.')


    def _raise_child(self):
        self._child()
        raise RuntimeError('This child error is expected.')


    def _assert_expected_parent_stderr(self, error_msg):
        self.assertTrue(('first parent error' in error_msg), error_msg)
        self.assertTrue(('second parent error' in error_msg), error_msg)
        self.assertTrue(
                (error_msg.index('first parent') <
                 error_msg.index('second parent')),
                'first and second errors out of order in:\n%r' % error_msg)
        self.assertEqual(2, error_msg.count('RuntimeError:'))


    def _assert_expected_child_stderr(self, error_msg):
        self.assertTrue('child error is expected' in error_msg)
        self.assertEqual(1, error_msg.count('RuntimeError:'), error_msg)


    def test_monkeypatching(self):
        if not hasattr(os, 'fork'):
            return  # Nothing to test on this platform.
        self.assertTrue(callable(atfork._orig_os_fork))
        self.assertTrue(callable(atfork._orig_os_forkpty))
        # The os module was patched, these should not be equal.
        self.assertNotEqual(atfork._orig_os_fork, os.fork)
        self.assertNotEqual(atfork._orig_os_forkpty, os.forkpty)
        # These are the wrapped versions we patched in.
        self.assertEqual(atfork.os_fork_wrapper, os.fork)
        self.assertEqual(atfork.os_forkpty_wrapper, os.forkpty)


    def test_register_atfork_calls(self):
        # Test with both positional and keyword arguments as well as None.
        atfork.atfork(self._pre, self._parent, self._child)
        atfork.atfork(prepare=self._pre)
        atfork.atfork(parent=self._parent)
        atfork.atfork(child=self._child)
        self.assertEqual([self._pre]*2, atfork._prepare_call_list)
        self.assertEqual([self._parent]*2, atfork._parent_call_list)
        self.assertEqual([self._child]*2, atfork._child_call_list)
        if __debug__:
            self.assertRaises(AssertionError, atfork.atfork, 1, 2, 3)


    def test_call_atfork_list(self):
        self.assertEqual([], atfork._call_atfork_list([]))
        self.assertEqual([], atfork._call_atfork_list([self._pre]))
        def raise_something():
            raise RuntimeError()
        errors = atfork._call_atfork_list([raise_something]*2)
        self.assertEqual(2, len(errors))
        for exc_info in errors:
            self.assertEqual(RuntimeError, exc_info[0])


    def _test_a_fork_wrapper(self, fork_func):
        sys.stderr = StringIO()  # restored in tearDown
        atfork.atfork(self._raise_pre, self._raise_parent, self._raise_child)
        atfork.atfork(self._other, self._other, self._other)
        pid = fork_func()
        if pid == 0:
            try:
                try:
                    self.assertEqual([self._pre, self._other,
                                      self._child, self._other], self.calls)
                    self.assertFalse(atfork._fork_lock.locked())
                    self._assert_expected_child_stderr(sys.stderr.getvalue())
                except:
                    try:
                        traceback.print_exc()
                        self.orig_stderr.write(sys.stderr.getvalue())
                    finally:
                        os._exit(1)
            finally:
                os._exit(0)
        else:
            self.assertEqual([self._pre, self._other,
                              self._parent, self._other], self.calls)
            self.assertFalse(atfork._fork_lock.locked())
            self.assertEqual(0, os.waitpid(pid, 0)[1], 'error in child')
        self._assert_expected_parent_stderr(sys.stderr.getvalue())


    def test_os_fork_wrapper(self):
        self._test_a_fork_wrapper(os.fork)


    def test_os_forkpty_wrapper(self):
        self._test_a_fork_wrapper(lambda: os.forkpty()[0])


    def _test_fork_failure(self, orig_fork_attrname, fork_wrapper):
        def failing_fork():
            raise OSError(0, 'testing a fork failure')
        atfork.atfork(self._pre, self._parent, self._child)
        orig_orig_fork = getattr(atfork, orig_fork_attrname)
        try:
            setattr(atfork, orig_fork_attrname, failing_fork)
            try:
                pid = fork_wrapper()
                if pid == 0:
                    # This should never happen but do this just in case.
                    os._exit(0)
            except OSError:
                self.assertEqual([self._pre, self._parent], self.calls)
            else:
                self.fail('Fork failed to fail!')
        finally:
            setattr(atfork, orig_fork_attrname, orig_orig_fork)


    def test_fork_wrapper_failure(self):
        self._test_fork_failure('_orig_os_fork', atfork.os_fork_wrapper)


    def test_forkpty_wrapper_failure(self):
        self._test_fork_failure('_orig_os_forkpty', atfork.os_forkpty_wrapper)


    def test_multiple_monkeypatch_safe(self):
        self.assertNotEqual(atfork._orig_os_fork, atfork.os_fork_wrapper)
        self.assertNotEqual(atfork._orig_os_forkpty, atfork.os_forkpty_wrapper)
        atfork.monkeypatch_os_fork_functions()
        self.assertNotEqual(atfork._orig_os_fork, atfork.os_fork_wrapper)
        self.assertNotEqual(atfork._orig_os_forkpty, atfork.os_forkpty_wrapper)
        atfork.monkeypatch_os_fork_functions()
        self.assertNotEqual(atfork._orig_os_fork, atfork.os_fork_wrapper)
        self.assertNotEqual(atfork._orig_os_forkpty, atfork.os_forkpty_wrapper)


if __name__ == '__main__':
    unittest.main()
