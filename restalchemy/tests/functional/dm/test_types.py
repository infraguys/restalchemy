# coding=utf-8
#
# Copyright 2014 Eugene Frolov <eugene@frolov.net.ru>
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import threading
import unittest

import six

from restalchemy.dm import types
from restalchemy.tests.functional import base


@unittest.skipUnless(six.PY2, "Actual only for python2")
class ThreadImportTestCase(base.BaseFunctionalTestCase):

    def test_strptime(self):
        exc_raised = [0]

        def f(exc_raised):
            try:
                for _ in range(1, 13):
                    for _ in range(1, 29):
                        types.UTCDateTime().from_simple_type(
                            '2013-01-01 00:00:00.0')
            except AttributeError:
                exc_raised[0] += 1

        pool = []
        for _ in range(10):
            thread = threading.Thread(target=f, args=(exc_raised,))
            pool.append(thread)
            thread.start()

        for thread in pool:
            thread.join()

        self.assertEqual(0, exc_raised[0])
