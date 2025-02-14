#    Copyright 2020 Eugene Frolov.
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
import sys

import pytest

from restalchemy.storage import base as sbase
from restalchemy.storage import exceptions
from restalchemy.tests.unit import base


class TestErrorCatcherTestCase(base.BaseTestCase):

    @sbase.error_catcher
    def my_func(self, *args, **kwargs):
        if args[0] == "test_arg" and kwargs.get("kwarg0") == "test_kwarg":
            raise RuntimeError(
                "Some Error!!!",
            )
        elif args[0] == "test_arg" and kwargs.get("kwarg0") == "RA_EXCEPTION":
            raise exceptions.RecordNotFound(model="FAKE", filters="FAKE")

    def test_catcher(self):
        self.assertRaises(
            exceptions.UnknownStorageException,
            self.my_func,
            "test_arg",
            kwarg0="test_kwarg",
        )

    def test_catcher_ra_exception(self):
        self.assertRaises(
            exceptions.RecordNotFound,
            self.my_func,
            "test_arg",
            kwarg0="RA_EXCEPTION",
        )

    @pytest.mark.skipif(sys.version_info > (3, 6), reason="python > 3.6")
    def test_catcher_message_error_lt_36(self):
        try:
            self.my_func("test_arg", kwarg0="test_kwarg")
            raise AssertionError("The exception is't raised")
        except exceptions.UnknownStorageException as e:
            self.assertEqual(
                str(e),
                "Unknown storage exception: RuntimeError('Some Error!!!',)",
            )

    @pytest.mark.skipif(sys.version_info < (3, 7), reason="python < 3.7")
    def test_catcher_message_error_gt_36(self):
        try:
            self.my_func("test_arg", kwarg0="test_kwarg")
            raise AssertionError("The exception is't raised")
        except exceptions.UnknownStorageException as e:
            self.assertEqual(
                str(e),
                "Unknown storage exception: RuntimeError('Some Error!!!')",
            )
