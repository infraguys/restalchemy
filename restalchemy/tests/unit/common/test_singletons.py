# Copyright 2023 v.burygin
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

import unittest

from restalchemy.common import singletons


class FakeMetaSingleton(metaclass=singletons.MetaSingleton):
    def __init__(self, prop1, prop2, *args, **kwargs):
        self._prop1 = prop1
        self._prop2 = prop2


class FakeInheritSingleton(singletons.InheritSingleton):
    def __init__(self, prop1, prop2, *args, **kwargs):
        self._prop1 = prop1
        self._prop2 = prop2


class TestSingletons(unittest.TestCase):

    def check_singletons(self, a, b):
        self.assertIs(a, b)
        self.assertTrue(a._prop1)
        self.assertTrue(b._prop1)
        self.assertEqual(a._prop2, ["a", "b", "c"])
        self.assertEqual(b._prop2, ["a", "b", "c"])

    def test_meta(self):
        a = FakeMetaSingleton(prop1=True, prop2=["a", "b", "c"])
        b = FakeMetaSingleton(prop1=False, prop2=["d", "e", "f"])
        self.check_singletons(a, b)

    def test_inherit(self):
        a = FakeInheritSingleton(prop1=True, prop2=["a", "b", "c"])
        b = FakeInheritSingleton(prop1=False, prop2=["d", "e", "f"])
        self.check_singletons(a, b)
