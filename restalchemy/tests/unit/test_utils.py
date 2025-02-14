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

from restalchemy.common import utils
from restalchemy.tests.unit import base


class ReadOnlyDictProxyTestCase(base.BaseTestCase):

    def test_is(self):
        self.assertFalse(
            utils.ReadOnlyDictProxy({1: 2}) is utils.ReadOnlyDictProxy({1: 2})
        )

    def test_equal(self):
        self.assertEqual(
            utils.ReadOnlyDictProxy({1: 2}), utils.ReadOnlyDictProxy({1: 2})
        )

    def test_len(self):
        self.assertEqual(len(utils.ReadOnlyDictProxy({1: 2, 2: 4})), 2)

    def test_getitem(self):
        self.assertEqual(utils.ReadOnlyDictProxy({1: 2, 2: 4})[1], 2)

    def test_hash(self):
        hash1 = hash(utils.ReadOnlyDictProxy({1: 2, 2: 4}))
        hash2 = hash(utils.ReadOnlyDictProxy({1: 2, 2: 4}))
        hash3 = hash(utils.ReadOnlyDictProxy({1: 2, 2: 3}))

        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash2, hash3)

    def test_readonly(self):
        dict1 = utils.ReadOnlyDictProxy({1: 2, 2: 4})

        def rotest(d):
            d[1] = 5

        self.assertRaises(TypeError, rotest, dict1)
