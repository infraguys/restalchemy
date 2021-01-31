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

import datetime
import re
import uuid

import mock
import six

from restalchemy.dm import types
from restalchemy.tests.unit import base


TEST_STR_VALUE = 'test_value :)'
TEST_INT_VALUE = 5
TEST_TYPE = 'FAKE TYPE'
INCORECT_UUID = '4a775g98-eg85-4a0e-a0g0-639f0a16f4c3'


@mock.patch("re.compile", return_value=mock.MagicMock(), autospec=True)
class BaseRegExpTypeTestCase(base.BaseTestCase):

    def _prepare_mock(self, re_mock, return_value):
        self.re_match_mock = mock.MagicMock(**{
            'match': mock.MagicMock(return_value=return_value)})
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

    def test_incorect_value(self, re_mock):
        self._prepare_mock(re_mock, None)

        test_instance = types.BaseRegExpType("")

        self.assertFalse(test_instance.validate(TEST_STR_VALUE))
        self.re_match_mock.match.assert_called_once_with(TEST_STR_VALUE)


class BaseTestCase(base.BaseTestCase):

    def __init__(self, *args, **kwargs):
        super(BaseTestCase, self).__init__(*args, **kwargs)
        self.test_instance = mock.MagicMock()
        self.test_instance.validate.configure_mock(**{'return_value': False})

    def test_correct_none_value(self):
        self.assertFalse(self.test_instance.validate(None))


class UUIDTestCase(base.BaseTestCase):

    def setUp(self):
        super(UUIDTestCase, self).setUp()
        self.test_instance = types.UUID()

    def test_uuid_correct_value(self):
        self.assertTrue(self.test_instance.validate(uuid.uuid4()))

    def test_uuid_incorrect_value(self):
        INCORECT_UUID = '4a775g98-eg85-4a0e-a0g0-639f0a16f4c3'

        self.assertFalse(self.test_instance.validate(
            INCORECT_UUID))

    def test_to_simple_type(self):
        TEST_UUID = uuid.uuid4()

        self.assertEqual(
            self.test_instance.to_simple_type(TEST_UUID),
            str(TEST_UUID))

    def test_from_simple_type(self):
        TEST_UUID = uuid.uuid4()

        self.assertEqual(
            self.test_instance.from_simple_type(str(TEST_UUID)),
            TEST_UUID)


class StringTestCase(base.BaseTestCase):

    FAKE_STRING1 = 'fake!!!'
    FAKE_STRING2 = six.u('fake!!!')

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
        self.assertTrue(self.test_instance1.validate(
            (self.FAKE_STRING1 * 2)[:8]))

    def test_correct_max_unicode_value(self):
        self.assertTrue(self.test_instance1.validate(
            (self.FAKE_STRING2 * 2)[:8]))

    def test_incorrect_min_value(self):
        self.assertFalse(self.test_instance1.validate(self.FAKE_STRING1[:4]))

    def test_incorrect_min_unicode_value(self):
        self.assertFalse(self.test_instance1.validate(self.FAKE_STRING1[:4]))

    def test_incorrect_max_value(self):
        self.assertFalse(self.test_instance1.validate(
            (self.FAKE_STRING1 * 2)[:9]))

    def test_incorrect_max_unicode_value(self):
        self.assertFalse(self.test_instance1.validate(
            (self.FAKE_STRING1 * 2)[:9]))

    def test_correct_infinity_value(self):
        self.assertTrue(self.test_instance2.validate(
            self.FAKE_STRING1 * 100500))

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

        self.assertTrue(test_instance.validate(six.MAXSIZE))

    def test_validate_sys_min_value(self):
        test_instance = types.Integer()

        self.assertTrue(test_instance.validate(-six.MAXSIZE))


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

        self.assertTrue(test_instance.validate(float(six.MAXSIZE)))

    def test_validate_sys_min_value(self):
        test_instance = types.Float()

        self.assertTrue(test_instance.validate(float(-six.MAXSIZE)))


class UriTestCase(BaseTestCase):

    def setUp(self):
        super(UriTestCase, self).setUp()
        self.test_instance = types.Uri()

    def test_correct_value(self):
        self.assertTrue(self.test_instance.validate(
            '/fake/fake/' + str(uuid.uuid4())))

    def test_incorect_uuid_value(self):
        self.assertFalse(self.test_instance.validate(
            '/fake/fake/' + INCORECT_UUID))

    def test_incorect_start_char_value(self):
        self.assertFalse(self.test_instance.validate(
            'fake/fake/' + str(uuid.uuid4())))

    def test_incorect_start_end_value(self):
        self.assertFalse(self.test_instance.validate(
            '/fake/fake' + str(uuid.uuid4())))


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

        self.test_instance = types.TypedList(nested_type=types.Integer())

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance.validate([]))
        self.assertTrue(self.test_instance.validate([1, 2, 3]))

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate([1, 2, '3', 4]))

    def test_incorrect_nested_type(self):
        self.assertRaises(TypeError, types.TypedList, int)


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
            'int': types.Integer(),
            'str': types.String(),
        }
        self.scheme_lists = {
            'list': types.List(),
            'typed_list': types.TypedList(types.Integer()),
        }
        self.scheme_dicts = {
            'dict': types.Dict(),
            'typed_dict': types.SchemeDict({
                'sub_str': types.String(),
                'sub_int': types.Integer(),
            }),
        }
        self.scheme_dict_sublist = {
            'typed_dict_with_typed_list': types.SchemeDict(
                {'sub_list_typed': types.TypedList(types.String())}),
        }
        self.scheme_dict_subdict = {
            'typed_dict_with_typed_dict': types.SchemeDict(
                {'sub_dict_typed': types.SchemeDict(
                    {
                        'sub_str': types.String(),
                        'sub_int': types.Integer(),
                    })}),
        }

    def test_schema_keys_not_string(self):
        self.assertRaises(ValueError, types.SchemeDict, {1: types.Integer()})

    def test_schema_values_not_types(self):
        self.assertRaises(ValueError, types.SchemeDict, {'1': int})

    def test_validate_simple_schema(self):
        dict_type = types.SchemeDict(scheme=self.scheme_simple_types)

        self.assertTrue(dict_type.validate({'int': 1, 'str': 'string'}))

    def test_validate_simple_schema_missing_item(self):
        dict_type = types.SchemeDict(scheme=self.scheme_simple_types)

        self.assertFalse(dict_type.validate({'int': 1}))
        self.assertFalse(dict_type.validate({'str': 'string'}))

    def test_validate_simple_schema_extra_item(self):
        dict_type = types.SchemeDict(scheme={'int': types.Integer()})

        self.assertFalse(dict_type.validate({'int': 1, 'str': 'string'}))

    def test_validate_simple_schema_invalid_value(self):
        dict_type_1 = types.SchemeDict(scheme={'int': types.Integer()})
        dict_type_2 = types.SchemeDict(scheme={'str': types.String()})

        self.assertFalse(dict_type_1.validate({'int': '1'}))
        self.assertFalse(dict_type_2.validate({'str': None}))

    def test_validate_schema_with_lists(self):
        schema = {'mixed_list': types.List()}
        schema.update(self.scheme_simple_types)
        schema.update(self.scheme_lists)

        dict_type = types.SchemeDict(scheme=schema)

        self.assertTrue(
            dict_type.validate({'int': 1,
                                'str': 'string',
                                'list': [1, 2, 3],
                                'mixed_list': [1, 'a', None],
                                'typed_list': [1, 2, 3]}))

    def test_validate_schema_incorrect_typed_list_value(self):
        schema = {'typed_list': types.TypedList(types.Integer())}

        dict_type = types.SchemeDict(scheme=schema)

        self.assertFalse(dict_type.validate({'typed_list': [1, '2', 3]}))
        self.assertFalse(dict_type.validate({'typed_list': [None, 2, 3]}))
        self.assertFalse(dict_type.validate({'typed_list': [1, 2, {}]}))

    def test_validate_schema_with_dicts(self):
        schema = {}
        schema.update(self.scheme_simple_types)
        schema.update(self.scheme_dicts)

        dict_type = types.SchemeDict(scheme=schema)

        self.assertTrue(
            dict_type.validate({'int': 1,
                                'str': 'string',
                                'dict': {'1': 1, '2': 'a', 'z': 3},
                                'typed_dict': {
                                    'sub_str': 'string',
                                    'sub_int': 42,
                                }}))

    def test_validate_schema_subdict_missing_item(self):
        schema = {}
        schema.update(self.scheme_simple_types)
        schema.update(self.scheme_dicts)

        dict_type = types.SchemeDict(scheme=schema)

        self.assertFalse(
            dict_type.validate({'int': 1,
                                'str': 'string',
                                'dict': {1: 1, 2: 'a', 'z': 3},
                                'typed_dict': {
                                    'sub_str': 'string',
                                }}))

    def test_validate_complex_schema(self):
        schema = {}
        schema.update(self.scheme_simple_types)
        schema.update(self.scheme_lists)
        schema.update(self.scheme_dicts)
        schema.update(self.scheme_dict_sublist)
        schema.update(self.scheme_dict_subdict)

        dict_type = types.SchemeDict(scheme=schema)

        self.assertTrue(
            dict_type.validate({'int': 1,
                                'str': 'string',
                                'list': ['a'],
                                'typed_list': [],
                                'dict': {},
                                'typed_dict': {
                                    'sub_str': 'string',
                                    'sub_int': 42},
                                'typed_dict_with_typed_list': {
                                    'sub_list_typed': ['s']
                                },
                                'typed_dict_with_typed_dict': {
                                    'sub_dict_typed': {
                                        'sub_str': 'string_2',
                                        'sub_int': -5}
                                },
                                }))


class UTCDateTimeTestCase(base.BaseTestCase):

    def setUp(self):
        super(UTCDateTimeTestCase, self).setUp()

        self.test_instance = types.UTCDateTime()

    def test_validate_correct_value(self):
        self.assertTrue(
            self.test_instance.validate(datetime.datetime.utcnow()))

    def test_validate_incorrect_value_type(self):
        self.assertFalse(self.test_instance.validate(TEST_STR_VALUE))

    def test_validate_incorrect_value_tzinfo(self):
        self.assertFalse(
            self.test_instance.validate(
                datetime.datetime.utcnow().replace(tzinfo=datetime.tzinfo())))

    def test_zero_microseconds(self):
        dt = datetime.datetime(2020, 3, 13, 11, 3, 25)
        expected = '2020-03-13 11:03:25.000000'
        dt_type = types.UTCDateTime()

        result = dt_type.to_simple_type(dt)

        self.assertEqual(result, expected)


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

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance.validate(None))
        self.assertTrue(self.test_instance.validate('string'))

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate(4))


class HostnameTestCase(base.BaseTestCase):

    def setUp(self):
        super(HostnameTestCase, self).setUp()

        self.test_instance = types.Hostname()

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance.validate('ns1.mcs.mail.ru'))
        self.assertTrue(self.test_instance.validate('ns1.55.mail.ru'))
        self.assertTrue(self.test_instance.validate('n_s1.55.mail.ru'))
        self.assertTrue(self.test_instance.validate('n-1.55.mail.ru'))
        self.assertTrue(self.test_instance.validate('mail.ru'))

    def test_validate_cyrillic_correct_value(self):
        self.assertTrue(self.test_instance.validate(u'xx.москва.рф'))
        self.assertTrue(self.test_instance.validate(u'москва.рф'))

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate('x.y.z'))
        self.assertFalse(self.test_instance.validate('mail.ru.'))
        self.assertFalse(self.test_instance.validate('mail.ru.55'))
        self.assertFalse(self.test_instance.validate('-1.55.mail.ru'))
        self.assertFalse(self.test_instance.validate('_s1.55.mail.ru'))
        self.assertFalse(self.test_instance.validate('.mail.ru'))
