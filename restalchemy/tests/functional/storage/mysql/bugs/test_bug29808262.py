# Copyright 2021 Eugene Frolov <eugene@frolov.net.ru>
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

import uuid

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types as ra_types
from restalchemy.storage.sql import orm
from restalchemy.tests.functional import base


FAKE_UUID_1 = uuid.UUID("63cf2e1a-4f1f-11ec-8f05-1bfa6ad82a13")
FAKE_UUID_2 = uuid.UUID("78e4a492-4f1f-11ec-abd3-c362c434cef3")


class BinaryField(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "binary_data"

    data = properties.property(ra_types.String(), required=True)


class Bug29808262TestCase(base.BaseWithDbMigrationsTestCase):

    __LAST_MIGRATION__ = "0001-test-bug-29808262-743d38"
    __FIRST_MIGRATION__ = "0001-test-bug-29808262-743d38.py"

    def test_blob_like_string(self):
        target = BinaryField(
            uuid=FAKE_UUID_1,
            data="aaa" * 1024,
        )
        target.insert()

        result = BinaryField.objects.get_one()

        self.assertEqual(result.data, target.data)

    def test_blob_like_float_bug29808262(self):
        target = BinaryField(
            uuid=FAKE_UUID_1,
            data="2" * 1024,
        )
        target.insert()

        # if bug is reproduced you will show like:
        # TypeError: Invalid type value 'inf' for 'String'
        result = BinaryField.objects.get_one()

        self.assertEqual(result.data, target.data)
