#    Copyright 2021 Eugene Frolov <eugene@frolov.net.ru>.
#
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

from restalchemy.tests.functional import base
from restalchemy.tests.functional.storage.mysql.prefetch import models


class PrefetchTestCase(base.BaseWithDbMigrationsTestCase):

    __LAST_MIGRATION__ = "prefetch-relationship-tests-data-9727f3"
    __FIRST_MIGRATION__ = "prefetch-relationship-tests-f3841e"

    def setUp(self):
        super(PrefetchTestCase, self).setUp()

        models.OBJECT_COLLECTION_MOCK.reset_mock()

    def test_get_model_without_relationships(self):

        results = models.Root.objects.get_all()

        self.assertEqual(1, len(results))
        self.assertEqual(1, models.OBJECT_COLLECTION_MOCK.get_all.call_count)

    def test_get_model_with_relationships_and_prefetch_false(self):
        results = models.LNP1_1.objects.get_all()

        self.assertEqual(1, len(results))
        self.assertEqual(2, models.OBJECT_COLLECTION_MOCK.get_all.call_count)

    def test_get_model_with_relationships_and_prefetch_true(self):
        results = models.LWP1_1.objects.get_all()

        self.assertEqual(1, len(results))
        self.assertEqual(1, models.OBJECT_COLLECTION_MOCK.get_all.call_count)

    def test_get_model_with_deep_relationships_and_prefetch_true(self):
        results = models.LWP2_1.objects.get_all()

        self.assertEqual(1, len(results))
        self.assertIsInstance(results[0], models.LWP2_1)
        self.assertIsInstance(results[0].lwp1_1, models.LWP1_1)
        self.assertIsInstance(results[0].lwp1_1.root, models.Root)
        self.assertEqual(1, models.OBJECT_COLLECTION_MOCK.get_all.call_count)

    def test_get_model_with_relationships_is_none_and_prefetch_true(self):
        results = models.LWP1_2.objects.get_all()

        self.assertEqual(1, len(results))
        self.assertIsInstance(results[0], models.LWP1_2)
        self.assertIsInstance(results[0].root, type(None))
        self.assertEqual(1, models.OBJECT_COLLECTION_MOCK.get_all.call_count)
