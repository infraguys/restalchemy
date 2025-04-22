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

import datetime
import decimal
import re
import sys
import uuid

import mock

from restalchemy.dm import types
from restalchemy.tests.unit import base


TEST_STR_VALUE = "test_value :)"
TEST_INT_AS_STR_VALUE = "1234"
TEST_INT_VALUE = 5
TEST_TYPE = "FAKE TYPE"
INCORECT_UUID = "4a775g98-eg85-4a0e-a0g0-639f0a16f4c3"
INCORECT_INT_AS_STR = "123abc"


@mock.patch("re.compile", return_value=mock.MagicMock(), autospec=True)
class BaseRegExpTypeTestCase(base.BaseTestCase):

    def _prepare_mock(self, re_mock, return_value):
        self.re_match_mock = mock.MagicMock(
            **{"match": mock.MagicMock(return_value=return_value)}
        )
        re_mock.return_value = self.re_match_mock

    def test_correct_value_if_value_is_not_none(self, re_mock):
        self._prepare_mock(re_mock, re.match("a", "a"))

        test_instance = types.BaseRegExpType("")

        self.assertTrue(test_instance.validate(TEST_STR_VALUE))
        self.re_match_mock.match.assert_called_once_with(TEST_STR_VALUE)

    def test_correct_value_if_value_is_none(self, re_mock):
        self._prepare_mock(re_mock, None)

        test_instance = types.BaseRegExpType("")

        self.assertFalse(test_instance.validate(None))

    def test_incorrect_value(self, re_mock):
        self._prepare_mock(re_mock, None)

        test_instance = types.BaseRegExpType("")

        self.assertFalse(test_instance.validate(TEST_STR_VALUE))
        self.re_match_mock.match.assert_called_once_with(TEST_STR_VALUE)


class BaseCompiledRegExpTypeTestCase(base.BaseTestCase):

    def test_correct_value_if_value_is_not_none(self):
        test_instance = types.BaseCompiledRegExpType(re.compile(r"t"))

        self.assertTrue(test_instance.validate(TEST_STR_VALUE))

    def test_correct_value_if_value_is_none(self):
        test_instance = types.BaseCompiledRegExpType(re.compile(r""))

        self.assertFalse(test_instance.validate(None))

    def test_incorrect_value(self):
        test_instance = types.BaseCompiledRegExpType(re.compile(r"-"))

        self.assertFalse(test_instance.validate(TEST_STR_VALUE))

    def test_get_pattern_from_attribute(self):
        class TestType(types.BaseCompiledRegExpTypeFromAttr):
            pattern = re.compile(r"t")

        test_instance = TestType()

        self.assertTrue(test_instance.validate(TEST_STR_VALUE))


class BaseTestCase(base.BaseTestCase):

    def __init__(self, *args, **kwargs):
        super(BaseTestCase, self).__init__(*args, **kwargs)
        self.test_instance = mock.MagicMock()
        self.test_instance.validate.configure_mock(**{"return_value": False})

    def test_correct_none_value(self):
        self.assertFalse(self.test_instance.validate(None))


class UUIDTestCase(base.BaseTestCase):

    def setUp(self):
        super(UUIDTestCase, self).setUp()
        self.test_instance = types.UUID()

    def test_uuid_correct_value(self):
        self.assertTrue(self.test_instance.validate(uuid.uuid4()))

    def test_uuid_incorrect_value(self):
        INCORECT_UUID = "4a775g98-eg85-4a0e-a0g0-639f0a16f4c3"

        self.assertFalse(self.test_instance.validate(INCORECT_UUID))

    def test_to_simple_type(self):
        TEST_UUID = uuid.uuid4()

        self.assertEqual(
            self.test_instance.to_simple_type(TEST_UUID), str(TEST_UUID)
        )

    def test_from_simple_type(self):
        TEST_UUID = uuid.uuid4()

        self.assertEqual(
            self.test_instance.from_simple_type(str(TEST_UUID)), TEST_UUID
        )

    def test_from_simple_type_uuid(self):
        TEST_UUID = uuid.uuid4()

        self.assertEqual(
            self.test_instance.from_simple_type(TEST_UUID), TEST_UUID
        )


class EmailTestCase(base.BaseTestCase):

    def setUp(self):
        super(EmailTestCase, self).setUp()
        self.test_instance1 = types.Email()
        self.test_instance2 = types.Email(5, 10)
        self.test_instance3 = types.Email(5, 100, check_deliverability=True)

    def test_correct_email_value(self):
        CORRECT_EMAIL = "eugene@frolov.net.ru"

        self.assertTrue(self.test_instance1.validate(CORRECT_EMAIL))

    def test_correct_short_email_value(self):
        CORRECT_EMAIL = "a@b.c"

        self.assertTrue(self.test_instance1.validate(CORRECT_EMAIL))

    def test_incorrect_email_value(self):
        INCORRECT_EMAIL = "eugene@frolov"

        self.assertFalse(self.test_instance1.validate(INCORRECT_EMAIL))

    def test_incorrect_very_short_email_value(self):
        INCORECT_EMAIL = "x@x"

        self.assertFalse(self.test_instance1.validate(INCORECT_EMAIL))

    def test_deliverability_email_value(self):
        CORRECT_DELIVERABLE_EMAIL = "eugene@gmail.com"

        self.assertTrue(
            self.test_instance3.validate(CORRECT_DELIVERABLE_EMAIL)
        )

    def test_email_to_very_long_value(self):
        INCORRECT_EMAIL = "eugene@gmail.com"

        self.assertFalse(self.test_instance2.validate(INCORRECT_EMAIL))

    def test_non_deliverability_email_value(self):
        CORRECT_NOT_DELIVERABLE_EMAIL = "eugene@frolov.incorrectzone"

        self.assertFalse(
            self.test_instance3.validate(CORRECT_NOT_DELIVERABLE_EMAIL)
        )


class StringTestCase(base.BaseTestCase):

    FAKE_STRING1 = "fake!!!"
    FAKE_STRING2 = "fake!!!"

    def setUp(self):
        super(StringTestCase, self).setUp()
        self.test_instance1 = types.String(min_length=5, max_length=8)
        self.test_instance2 = types.String()

    def test_correct_value(self):
        self.assertTrue(self.test_instance1.validate(self.FAKE_STRING1))

    def test_correct_unicode_value(self):
        self.assertTrue(self.test_instance1.validate(self.FAKE_STRING2))

    def test_correct_min_value(self):
        self.assertTrue(self.test_instance1.validate(self.FAKE_STRING1[:5]))

    def test_correct_min_unicode_value(self):
        self.assertTrue(self.test_instance1.validate(self.FAKE_STRING2[:5]))

    def test_correct_max_value(self):
        self.assertTrue(
            self.test_instance1.validate((self.FAKE_STRING1 * 2)[:8])
        )

    def test_correct_max_unicode_value(self):
        self.assertTrue(
            self.test_instance1.validate((self.FAKE_STRING2 * 2)[:8])
        )

    def test_incorrect_min_value(self):
        self.assertFalse(self.test_instance1.validate(self.FAKE_STRING1[:4]))

    def test_incorrect_min_unicode_value(self):
        self.assertFalse(self.test_instance1.validate(self.FAKE_STRING1[:4]))

    def test_incorrect_max_value(self):
        self.assertFalse(
            self.test_instance1.validate((self.FAKE_STRING1 * 2)[:9])
        )

    def test_incorrect_max_unicode_value(self):
        self.assertFalse(
            self.test_instance1.validate((self.FAKE_STRING1 * 2)[:9])
        )

    def test_correct_infinity_value(self):
        self.assertTrue(
            self.test_instance2.validate(self.FAKE_STRING1 * 100500)
        )

    def test_incorrect_type_validate(self):
        self.assertFalse(self.test_instance1.validate(5))


class IntegerTestCase(base.BaseTestCase):

    def setUp(self):
        super(IntegerTestCase, self).setUp()

        self.test_instance = types.Integer(0, 55)

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance.validate(30))

    def test_validate_correct_max_value(self):
        self.assertTrue(self.test_instance.validate(55))

    def test_validate_correct_min_value(self):
        self.assertTrue(self.test_instance.validate(0))

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate("TEST_STR_VALUE"))

    def test_validate_incorrect_max_value(self):
        self.assertFalse(self.test_instance.validate(56))

    def test_validate_incorrect_min_value(self):
        self.assertFalse(self.test_instance.validate(-1))

    def test_validate_sys_max_value(self):
        test_instance = types.Integer()

        self.assertTrue(test_instance.validate(sys.maxsize))

    def test_validate_sys_min_value(self):
        test_instance = types.Integer()

        self.assertTrue(test_instance.validate(-sys.maxsize))


class FloatTestCase(base.BaseTestCase):

    def setUp(self):
        super(FloatTestCase, self).setUp()

        self.test_instance = types.Float(0.0, 55.0)

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance.validate(30.0))

    def test_validate_correct_max_value(self):
        self.assertTrue(self.test_instance.validate(55.0))

    def test_validate_correct_min_value(self):
        self.assertTrue(self.test_instance.validate(0.0))

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate("TEST_STR_VALUE"))

    def test_validate_incorrect_max_value(self):
        self.assertFalse(self.test_instance.validate(56.0))

    def test_validate_incorrect_min_value(self):
        self.assertFalse(self.test_instance.validate(-1.0))

    def test_validate_sys_max_value(self):
        test_instance = types.Float()

        self.assertTrue(test_instance.validate(float(sys.maxsize)))

    def test_validate_sys_min_value(self):
        test_instance = types.Float()

        self.assertTrue(test_instance.validate(float(-sys.maxsize)))


class DecimalTestCase(base.BaseTestCase):

    def setUp(self):
        super().setUp()

        self.test_instance = types.Decimal(0.0, 55.0)

    def test_validate_decimal_roundup(self):
        assert types.Decimal().from_simple_type(
            "0.1"
        ) + types.Decimal().from_simple_type(
            "0.1"
        ) + types.Decimal().from_simple_type(
            "0.1"
        ) == decimal.Decimal(
            "0.3"
        )

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance.validate(decimal.Decimal(30.0)))

    def test_validate_correct_max_value(self):
        self.assertTrue(self.test_instance.validate(decimal.Decimal(55.0)))

    def test_validate_correct_min_value(self):
        self.assertTrue(self.test_instance.validate(decimal.Decimal(0.0)))

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate("TEST_STR_VALUE"))

    def test_validate_incorrect_max_value(self):
        self.assertFalse(self.test_instance.validate(decimal.Decimal(56.0)))

    def test_validate_incorrect_min_value(self):
        self.assertFalse(self.test_instance.validate(decimal.Decimal(-1.0)))

    def test_validate_sys_max_value(self):
        test_instance = types.Decimal()

        self.assertTrue(test_instance.validate(decimal.Decimal(sys.maxsize)))

    def test_validate_sys_min_value(self):
        test_instance = types.Decimal()

        self.assertTrue(test_instance.validate(decimal.Decimal(-sys.maxsize)))

    def test_validate_correct_max_decimal_places(self):
        test_instance = types.Decimal(max_decimal_places=2)

        self.assertTrue(test_instance.validate(decimal.Decimal("2.22")))

    def test_validate_incorrect_max_decimal_places(self):
        test_instance = types.Decimal(max_decimal_places=2)

        self.assertFalse(test_instance.validate(decimal.Decimal("2.222")))


class UriTestCase(BaseTestCase):

    def setUp(self):
        super(UriTestCase, self).setUp()
        self.test_instance = types.Uri()

    def test_correct_value(self):
        self.assertTrue(
            self.test_instance.validate("/fake/fake/" + str(uuid.uuid4()))
        )

    def test_incorect_uuid_value(self):
        self.assertFalse(
            self.test_instance.validate("/fake/fake/" + INCORECT_UUID)
        )

    def test_incorect_start_char_value(self):
        self.assertFalse(
            self.test_instance.validate("fake/fake/" + str(uuid.uuid4()))
        )

    def test_incorect_start_end_value(self):
        self.assertFalse(
            self.test_instance.validate("/fake/fake" + str(uuid.uuid4()))
        )


class MacTestCase(BaseTestCase):

    def setUp(self):
        super(MacTestCase, self).setUp()
        self.test_instance = types.Mac()

    def get_values(self, value):
        return [value, value.upper()]

    def test_correct_value(self):
        for value in self.get_values("05:06:07:08:ab:ff"):
            self.assertTrue(self.test_instance.validate(value))

    def test_incorrect_cahar_value(self):
        for value in self.get_values("05:06:0k:08:ab:ff"):
            self.assertFalse(self.test_instance.validate(value))

    def test_incorrect_length_value(self):
        for value in self.get_values("05:06:08:ab:ff"):
            self.assertFalse(self.test_instance.validate(value))


class BasePythonTypeTestCase(base.BaseTestCase):

    def setUp(self):
        super(BasePythonTypeTestCase, self).setUp()

        self.test_instance = types.BasePythonType(int)

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance.validate(TEST_INT_VALUE))

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate(TEST_STR_VALUE))


class ListTestCase(base.BaseTestCase):

    def setUp(self):
        super(ListTestCase, self).setUp()

        self.test_instance = types.List()

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance.validate(list()))

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate(TEST_STR_VALUE))


class TypedListTestCase(base.BaseTestCase):

    def setUp(self):
        super(TypedListTestCase, self).setUp()

        self.test_instance_int = types.TypedList(nested_type=types.Integer())
        self.test_instance_str = types.TypedList(nested_type=types.String())

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance_int.validate([]))
        self.assertTrue(self.test_instance_int.validate([1, 2, 3]))

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance_int.validate([1, 2, "3", 4]))

    def test_incorrect_nested_type(self):
        self.assertRaises(TypeError, types.TypedList, int)

    def test_from_unicode(self):
        payload = ((TEST_INT_AS_STR_VALUE, [int(TEST_INT_AS_STR_VALUE)]),)

        for value, expectedResult in payload:
            result = self.test_instance_int.from_unicode(value)
            self.assertEqual(expectedResult, result)

        payload = ((TEST_STR_VALUE, [TEST_STR_VALUE]),)

        for value, expectedResult in payload:
            result = self.test_instance_str.from_unicode(value)
            self.assertEqual(expectedResult, result)

        with self.assertRaises(TypeError):
            self.test_instance_int.from_unicode(None)
            self.test_instance_int.from_unicode(INCORECT_INT_AS_STR)


class DictTestCase(base.BaseTestCase):

    def setUp(self):
        super(DictTestCase, self).setUp()

        self.test_instance = types.Dict()

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance.validate(dict()))

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate(TEST_STR_VALUE))


class TypedDictTestCase(base.BaseTestCase):

    def setUp(self):
        super(TypedDictTestCase, self).setUp()

        self.scheme_simple_types = {
            "int": types.Integer(),
            "str": types.String(),
        }
        self.scheme_lists = {
            "list": types.List(),
            "typed_list": types.TypedList(types.Integer()),
        }
        self.scheme_dicts = {
            "dict": types.Dict(),
            "typed_dict": types.SchemeDict(
                {
                    "sub_str": types.String(),
                    "sub_int": types.Integer(),
                }
            ),
        }
        self.scheme_dict_sublist = {
            "typed_dict_with_typed_list": types.SchemeDict(
                {"sub_list_typed": types.TypedList(types.String())}
            ),
        }
        self.scheme_dict_subdict = {
            "typed_dict_with_typed_dict": types.SchemeDict(
                {
                    "sub_dict_typed": types.SchemeDict(
                        {
                            "sub_str": types.String(),
                            "sub_int": types.Integer(),
                        }
                    )
                }
            ),
        }

    def test_schema_keys_not_string(self):
        self.assertRaises(ValueError, types.SchemeDict, {1: types.Integer()})

    def test_schema_values_not_types(self):
        self.assertRaises(ValueError, types.SchemeDict, {"1": int})

    def test_validate_simple_schema(self):
        dict_type = types.SchemeDict(scheme=self.scheme_simple_types)

        self.assertTrue(dict_type.validate({"int": 1, "str": "string"}))

    def test_validate_simple_schema_missing_item(self):
        dict_type = types.SchemeDict(scheme=self.scheme_simple_types)

        self.assertFalse(dict_type.validate({"int": 1}))
        self.assertFalse(dict_type.validate({"str": "string"}))

    def test_validate_simple_schema_extra_item(self):
        dict_type = types.SchemeDict(scheme={"int": types.Integer()})

        self.assertFalse(dict_type.validate({"int": 1, "str": "string"}))

    def test_validate_simple_schema_invalid_value(self):
        dict_type_1 = types.SchemeDict(scheme={"int": types.Integer()})
        dict_type_2 = types.SchemeDict(scheme={"str": types.String()})

        self.assertFalse(dict_type_1.validate({"int": "1"}))
        self.assertFalse(dict_type_2.validate({"str": None}))

    def test_validate_schema_with_lists(self):
        schema = {"mixed_list": types.List()}
        schema.update(self.scheme_simple_types)
        schema.update(self.scheme_lists)

        dict_type = types.SchemeDict(scheme=schema)

        self.assertTrue(
            dict_type.validate(
                {
                    "int": 1,
                    "str": "string",
                    "list": [1, 2, 3],
                    "mixed_list": [1, "a", None],
                    "typed_list": [1, 2, 3],
                }
            )
        )

    def test_validate_schema_incorrect_typed_list_value(self):
        schema = {"typed_list": types.TypedList(types.Integer())}

        dict_type = types.SchemeDict(scheme=schema)

        self.assertFalse(dict_type.validate({"typed_list": [1, "2", 3]}))
        self.assertFalse(dict_type.validate({"typed_list": [None, 2, 3]}))
        self.assertFalse(dict_type.validate({"typed_list": [1, 2, {}]}))

    def test_validate_schema_with_dicts(self):
        schema = {}
        schema.update(self.scheme_simple_types)
        schema.update(self.scheme_dicts)

        dict_type = types.SchemeDict(scheme=schema)

        self.assertTrue(
            dict_type.validate(
                {
                    "int": 1,
                    "str": "string",
                    "dict": {"1": 1, "2": "a", "z": 3},
                    "typed_dict": {
                        "sub_str": "string",
                        "sub_int": 42,
                    },
                }
            )
        )

    def test_validate_schema_subdict_missing_item(self):
        schema = {}
        schema.update(self.scheme_simple_types)
        schema.update(self.scheme_dicts)

        dict_type = types.SchemeDict(scheme=schema)

        self.assertFalse(
            dict_type.validate(
                {
                    "int": 1,
                    "str": "string",
                    "dict": {1: 1, 2: "a", "z": 3},
                    "typed_dict": {
                        "sub_str": "string",
                    },
                }
            )
        )

    def test_validate_complex_schema(self):
        schema = {}
        schema.update(self.scheme_simple_types)
        schema.update(self.scheme_lists)
        schema.update(self.scheme_dicts)
        schema.update(self.scheme_dict_sublist)
        schema.update(self.scheme_dict_subdict)

        dict_type = types.SchemeDict(scheme=schema)

        self.assertTrue(
            dict_type.validate(
                {
                    "int": 1,
                    "str": "string",
                    "list": ["a"],
                    "typed_list": [],
                    "dict": {},
                    "typed_dict": {"sub_str": "string", "sub_int": 42},
                    "typed_dict_with_typed_list": {"sub_list_typed": ["s"]},
                    "typed_dict_with_typed_dict": {
                        "sub_dict_typed": {
                            "sub_str": "string_2",
                            "sub_int": -5,
                        }
                    },
                }
            )
        )

    def test_scheme_dict_to_simple_type(self):
        val = 7
        ret_val = 9
        test_obj = self

        class TestType(types.Integer):
            def to_simple_type(self, data_val):
                test_obj.assertIs(val, data_val)
                return ret_val

        scheme = {
            "key": TestType(),
        }
        data = {
            "key": val,
        }
        expect_data = {"key": ret_val}

        res = types.SchemeDict(scheme=scheme).to_simple_type(data)
        self.assertEqual(expect_data, res)


class UTCDateTimeTestCase(base.BaseTestCase):

    def setUp(self):
        super(UTCDateTimeTestCase, self).setUp()

        self.test_instance = types.UTCDateTime()

    def test_validate_correct_value_with_explicit_utc_tz(self):
        self.assertTrue(
            self.test_instance.validate(
                datetime.datetime.now(datetime.timezone.utc)
            )
        )

    def test_validate_correct_value(self):
        self.assertTrue(
            self.test_instance.validate(datetime.datetime.utcnow())
        )

    def test_validate_incorrect_value_type(self):
        self.assertFalse(self.test_instance.validate(TEST_STR_VALUE))

    def test_validate_incorrect_value_tzinfo(self):
        self.assertFalse(
            self.test_instance.validate(
                datetime.datetime.utcnow().replace(tzinfo=datetime.tzinfo())
            )
        )

    def test_zero_microseconds(self):
        dt = datetime.datetime(2020, 3, 13, 11, 3, 25)
        expected = "2020-03-13 11:03:25.000000"
        dt_type = types.UTCDateTime()

        result = dt_type.to_simple_type(dt)

        self.assertEqual(result, expected)

    def test_openapi_format(self):
        dt = datetime.datetime(2020, 3, 13, 11, 3, 25, 123)

        expected = "2020-03-13T11:03:25.000123Z"
        dt_type = types.UTCDateTime()

        result = dt_type.dump_value(dt)

        self.assertEqual(result, expected)

        result = dt_type.from_simple_type(expected)
        self.assertEqual(result, dt)


class UTCDateTimeZTestCase(base.BaseTestCase):

    def setUp(self):
        super(UTCDateTimeZTestCase, self).setUp()

        self.test_instance = types.UTCDateTimeZ()

    def test_validate_correct_value_with_explicit_utc_tz(self):
        self.assertTrue(
            self.test_instance.validate(
                datetime.datetime.now(datetime.timezone.utc)
            )
        )

    def test_validate_incorrect_value_wo_tz(self):
        self.assertFalse(self.test_instance.validate(datetime.datetime.now()))

    def test_validate_from_simple_type_wo_tz(self):
        dt = datetime.datetime(2020, 3, 13, 11, 3, 25)
        expected = "2020-03-13 11:03:25.000000"

        result = types.UTCDateTimeZ().from_simple_type(dt)

        self.assertEqual(result, dt.replace(tzinfo=datetime.timezone.utc))
        self.assertIsNone(dt.tzinfo)
        self.assertEqual(result.tzinfo, datetime.timezone.utc)

    def test_validate_from_simple_type_with_tz(self):
        dtz = datetime.datetime.fromisoformat("2020-03-13T11:03:25+03:00")
        expected_utc = "2020-03-13 08:03:25.000000"

        result = types.UTCDateTimeZ().from_simple_type(dtz)

        self.assertEqual(
            dtz.tzinfo, datetime.timezone(datetime.timedelta(seconds=10800))
        )
        self.assertEqual(result.tzinfo, datetime.timezone.utc)
        self.assertEqual(result, dtz.astimezone(datetime.timezone.utc))
        self.assertEqual(
            types.UTCDateTimeZ().to_simple_type(result), expected_utc
        )


class EnumTestCase(base.BaseTestCase):

    def setUp(self):
        super(EnumTestCase, self).setUp()

        self.test_instance = types.Enum([1, 2, 3])

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance.validate(1))

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate(4))


class AllowNoneTestCase(base.BaseTestCase):

    def setUp(self):
        super(AllowNoneTestCase, self).setUp()

        self.test_instance = types.AllowNone(types.String())

    def test_from_unicode(self):
        s = "blah273 2 s3d3"
        self.assertEqual(self.test_instance.from_unicode(s), s)
        self.assertIsNone(self.test_instance.from_unicode("null"))

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance.validate(None))
        self.assertTrue(self.test_instance.validate("string"))

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate(4))


class HostnameTestCase(base.BaseTestCase):

    def setUp(self):
        super(HostnameTestCase, self).setUp()

        self.test_instance = types.Hostname()

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance.validate("ns1.ra.restalchemy.com"))
        self.assertTrue(self.test_instance.validate("ns1.55.restalchemy.com"))
        self.assertTrue(self.test_instance.validate("n_s1.55.restalchemy.com"))
        self.assertTrue(self.test_instance.validate("n-1.55.restalchemy.com"))
        self.assertTrue(self.test_instance.validate("restalchemy.com"))

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate("x.y.z"))
        self.assertFalse(self.test_instance.validate("restalchemy.com."))
        self.assertFalse(self.test_instance.validate("restalchemy.com.55"))
        self.assertFalse(self.test_instance.validate("-1.55.restalchemy.com"))
        self.assertFalse(self.test_instance.validate("_s1.55.restalchemy.com"))
        self.assertFalse(self.test_instance.validate(".restalchemy.com"))
        self.assertFalse(self.test_instance.validate("xx.москва.рф"))
        self.assertFalse(self.test_instance.validate("москва.рф"))


class UrlTestCase(base.BaseTestCase):

    def setUp(self):
        super(UrlTestCase, self).setUp()

        self.test_instance = types.Url()

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance.validate("http://www.gmail.com"))
        self.assertTrue(
            self.test_instance.validate("https://www.gmail.com/test")
        )

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate("x.y.z"))
        self.assertFalse(self.test_instance.validate(532))
        self.assertFalse(self.test_instance.validate("google.com.55"))


class SoftSchemeDictTestCase(base.BaseTestCase):

    def setUp(self):
        super(SoftSchemeDictTestCase, self).setUp()

        self.scheme = {
            "sub_str": types.String(),
            "sub_int": types.Integer(),
        }
        self.correct_simple_data = {
            "sub_str": "substr",
            "sub_int": 7,
        }
        self.test_instance = types.SoftSchemeDict(scheme=self.scheme)

    def test_from_simple_type(self):
        self._test_from_simple_type(
            self.test_instance, self.scheme, self.correct_simple_data
        )

    def test_from_simple_type_keys_missing(self):
        data = self.correct_simple_data.copy()
        del data[next(iter(data.keys()))]

        self._test_from_simple_type(self.test_instance, self.scheme, data)

    def test_from_simple_type_empty_data(self):
        self._test_from_simple_type(self.test_instance, self.scheme, {})

    def test_from_simple_type_extra_keys(self):
        data = self.correct_simple_data.copy()
        data["some_key"] = object()

        self.assertRaises(
            KeyError,
            self._test_from_simple_type,
            self.test_instance,
            self.scheme,
            data,
        )

    def test_validate_correct_value(self):
        value = self.test_instance.from_simple_type(self.correct_simple_data)

        self.assertTrue(
            self._test_validate(self.test_instance, self.scheme, value)
        )

    def test_validate_incorrect_value(self):
        value = self.test_instance.from_simple_type(self.correct_simple_data)
        value[next(iter(value.keys()))] = object()

        self.assertFalse(
            self._test_validate(self.test_instance, self.scheme, value)
        )

    def test_validate_keys_missing(self):
        data = self.correct_simple_data.copy()
        del data[next(iter(data.keys()))]
        value = self.test_instance.from_simple_type(data)

        self.assertTrue(
            self._test_validate(self.test_instance, self.scheme, value)
        )

    def test_validate_soft_scheme_dict_empty(self):
        value = self.test_instance.from_simple_type({})

        self.assertTrue(
            self._test_validate(self.test_instance, self.scheme, value)
        )

    def test_validate_wrong_key(self):
        value = self.test_instance.from_simple_type(self.correct_simple_data)
        first_key = next(iter(value.keys()))
        value[first_key + "something"] = value.pop(first_key)

        self.assertFalse(
            self._test_validate(self.test_instance, self.scheme, value)
        )

    def _test_from_simple_type(self, typ_obj, scheme, data):
        arg_data = data.copy()

        with mock.patch.object(
            types.Dict, "from_simple_type", return_value=arg_data
        ) as dict_from_simple_type:
            val = typ_obj.from_simple_type(arg_data)

        self.assertEqual(data, arg_data)
        dict_from_simple_type.assert_called_once_with(arg_data)
        self.assertEqual(data, val)
        for key, data_item in data.items():
            self.assertIsInstance(val[key], type(data_item))

    def _test_validate(self, typ_obj, scheme, value):
        arg_value = value.copy()

        with mock.patch.object(
            types.Dict, "validate", return_value=True
        ) as dict_validate:
            ret = typ_obj.validate(arg_value)

        self.assertEqual(value, arg_value)
        dict_validate.assert_called_once_with(arg_value)

        return ret


class SchemaDictTestCase(base.BaseTestCase):
    def test_from_simple_type(self):
        scheme = {
            "sub_str": types.String(),
            "sub_int": types.Integer(),
        }

        test_instance = types.SchemeDict(scheme=scheme)
        self.assertEqual(
            test_instance.from_simple_type({}),
            {
                "sub_str": None,
                "sub_int": None,
            },
        )

    def test_to_simple_type(self):
        scheme = {
            "sub_str": types.String(),
            "sub_int": types.Integer(),
        }

        test_instance = types.SchemeDict(scheme=scheme)
        self.assertEqual(
            test_instance.to_simple_type(
                {
                    "sub_str": None,
                    "sub_int": None,
                }
            ),
            {
                "sub_str": None,
                "sub_int": None,
            },
        )

    def test_validate_wrong(self):
        scheme = {
            "sub_str": types.String(),
            "sub_int": types.Integer(),
        }

        test_instance = types.SchemeDict(scheme=scheme)
        value = test_instance.from_simple_type({})
        self.assertFalse(test_instance.validate(value))

    def test_validate_correct_value_allow_none(self):
        scheme = {
            "sub_str": types.AllowNone(types.String()),
            "sub_int": types.AllowNone(types.Integer()),
        }

        test_instance = types.SchemeDict(scheme=scheme)
        value = test_instance.from_simple_type({})
        self.assertTrue(test_instance.validate(value))

    def test_validate_with_correct_value(self):
        scheme = {
            "sub_str": types.String(),
            "sub_int": types.Integer(),
        }

        test_instance = types.SchemeDict(scheme=scheme)
        value = test_instance.from_simple_type(
            {
                "sub_int": 1,
                "sub_str": "Test",
            }
        )
        self.assertTrue(test_instance.validate(value))

    def test_validate_with_incorrect_value(self):
        scheme = {
            "sub_str": types.String(),
            "sub_int": types.Integer(),
        }

        test_instance = types.SchemeDict(scheme=scheme)
        value = test_instance.from_simple_type(
            {
                "sub_int": "Test",
                "sub_str": "Test",
            }
        )
        self.assertFalse(test_instance.validate(value))

    def test_validate_with_wrong_key(self):
        scheme = {
            "sub_str": types.String(),
            "sub_int": types.Integer(),
        }

        test_instance = types.SchemeDict(scheme=scheme)

        self.assertFalse(
            test_instance.validate(
                {"sub_int": 1, "sub_str": "Test", "sub_wrong": "wrong_key"}
            )
        )

    def test_validate_with_wrong_key_after_from_simple_type(self):
        scheme = {
            "sub_str": types.String(),
            "sub_int": types.Integer(),
        }

        test_instance = types.SchemeDict(scheme=scheme)
        value = test_instance.from_simple_type(
            {
                "sub_int": 1,
                "sub_str": "Test",
                "sub_wrong": "wrong_key",
            }
        )
        self.assertTrue(test_instance.validate(value))

    def test_validate_with_key_missing_after_from_simple_type(self):
        scheme = {
            "sub_str": types.String(),
            "sub_int": types.Integer(),
        }

        test_instance = types.SchemeDict(scheme=scheme)
        value = test_instance.from_simple_type(
            {
                "sub_int": 1,
            }
        )
        self.assertFalse(test_instance.validate(value))


class TimeDeltaTestCase(base.BaseTestCase):

    def setUp(self):
        super().setUp()
        self.test_instance = types.TimeDelta(-10.0, 50.0)

    def test_validate_correct_value(self):
        self.assertTrue(
            self.test_instance.validate(datetime.timedelta(seconds=10.0))
        )

    def test_validate_correct_max_value(self):
        self.assertTrue(
            self.test_instance.validate(datetime.timedelta(seconds=50))
        )

    def test_validate_correct_min_value(self):
        self.assertTrue(
            self.test_instance.validate(datetime.timedelta(seconds=-10))
        )

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate("TEST"))

    def test_validate_incorrect_max_value(self):
        self.assertFalse(
            self.test_instance.validate(datetime.timedelta(seconds=50.1))
        )

    def test_validate_incorrect_min_value(self):
        self.assertFalse(
            self.test_instance.validate(datetime.timedelta(seconds=-10.1))
        )

    def test_validate_sys_max_value(self):
        test_instance = types.TimeDelta()

        self.assertTrue(
            test_instance.validate(
                datetime.timedelta(seconds=types.TIMEDELTA_INFINITY)
            )
        )

    def test_validate_sys_min_value(self):
        test_instance = types.TimeDelta()

        self.assertTrue(
            test_instance.validate(
                datetime.timedelta(seconds=-types.TIMEDELTA_INFINITY)
            )
        )
