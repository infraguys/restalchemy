# Copyright 2014 Eugene Frolov <eugene@frolov.net.ru>
# Copyright 2025 Genesis Corporation
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

import mock

from restalchemy.common import exceptions
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.tests.unit import base

FAKE_VALUE = "FAKE_VALUE"
FAKE_VALUE2 = "FAKE_VALUE2"
FAKE_VALUE3 = "FAKE_VALUE3"


class PropertyTestCase(base.BaseTestCase):

    def setUp(self):
        super(PropertyTestCase, self).setUp()
        self.positive_fake_property_type = mock.MagicMock(
            **{
                "validate": mock.MagicMock(return_value=True),
                "spec": types.BaseType,
            }
        )
        self.negative_fake_property_type = mock.MagicMock(
            **{
                "validate": mock.MagicMock(return_value=False),
                "spec": types.BaseType,
            }
        )

    def _set_property_value(self, obj, value):
        obj.value = value

    def test_init_with_correct_value(self):
        property_obj = properties.Property(
            self.positive_fake_property_type, value=FAKE_VALUE
        )

        self.assertEqual(property_obj._value, FAKE_VALUE)
        self.positive_fake_property_type.validate.assert_called_with(
            FAKE_VALUE
        )

    def test_init_incorrect_value(self):
        self.assertRaises(
            exceptions.TypeError,
            properties.Property,
            self.negative_fake_property_type,
            value=FAKE_VALUE,
        )

    def test_init_default_value(self):
        property_obj = properties.Property(
            self.positive_fake_property_type, default=FAKE_VALUE
        )

        self.assertEqual(property_obj._value, FAKE_VALUE)
        self.positive_fake_property_type.validate.assert_called_with(
            FAKE_VALUE
        )

    def test_init_default_callable_value(self):
        property_obj = properties.Property(
            self.positive_fake_property_type, default=lambda: FAKE_VALUE
        )

        self.assertEqual(property_obj.value, FAKE_VALUE)
        self.positive_fake_property_type.validate.assert_called_with(
            FAKE_VALUE
        )

    def test_init_default_value_if_property_read_only(self):
        property_obj = properties.Property(
            self.positive_fake_property_type,
            default=FAKE_VALUE,
            read_only=True,
        )

        self.assertEqual(property_obj._value, FAKE_VALUE)
        self.positive_fake_property_type.validate.assert_called_with(
            FAKE_VALUE
        )

    def test_init_none_and_require(self):
        self.assertRaises(
            exceptions.PropertyRequired,
            properties.Property,
            self.negative_fake_property_type,
            required=True,
            value=None,
        )

    def test_init_value_is_none_default_is_not_none_and_prop_required(self):
        property_obj = properties.Property(
            self.positive_fake_property_type,
            value=None,
            required=True,
            default=FAKE_VALUE,
        )

        self.assertEqual(property_obj._value, FAKE_VALUE)
        self.positive_fake_property_type.validate.assert_called_with(
            FAKE_VALUE
        )

    def test_init_none_value(self):
        property_obj = properties.Property(
            self.negative_fake_property_type, value=None
        )

        self.assertEqual(property_obj._value, None)

    def test_init_value_with_read_only(self):
        property_obj = properties.Property(
            self.positive_fake_property_type, read_only=True, value=FAKE_VALUE2
        )

        self.assertEqual(property_obj._value, FAKE_VALUE2)
        self.positive_fake_property_type.validate.assert_called_with(
            FAKE_VALUE2
        )

    def test_set_correct_value(self):
        property_obj = properties.Property(self.positive_fake_property_type)

        self.assertIsNone(self._set_property_value(property_obj, FAKE_VALUE))
        self.assertEqual(property_obj._value, FAKE_VALUE)
        self.positive_fake_property_type.validate.assert_called_with(
            FAKE_VALUE
        )

    def test_set_incorect_value(self):
        property_obj = properties.Property(self.negative_fake_property_type)
        old_value = property_obj._value

        self.assertRaises(
            exceptions.TypeError,
            self._set_property_value,
            property_obj,
            FAKE_VALUE,
        )
        self.assertEqual(property_obj._value, old_value)
        self.negative_fake_property_type.validate.assert_called_with(
            FAKE_VALUE
        )

    def test_set_value_if_property_read_only(self):
        property_obj = properties.Property(
            self.positive_fake_property_type, read_only=True
        )

        self.assertRaises(
            exceptions.ReadOnlyProperty,
            self._set_property_value,
            property_obj,
            FAKE_VALUE2,
        )
        self.assertEqual(property_obj._value, None)

    def test_set_value_if_property_read_only_and_value_is_same(self):
        property_obj = properties.Property(
            self.positive_fake_property_type, read_only=True, value=FAKE_VALUE
        )

        self.assertIsNone(self._set_property_value(property_obj, FAKE_VALUE))
        self.assertEqual(property_obj._value, FAKE_VALUE)

    def test_set_value_if_property_read_only_and_value_is_different(self):
        property_obj = properties.Property(
            self.positive_fake_property_type, read_only=True, value=FAKE_VALUE
        )

        self.assertRaises(
            exceptions.ReadOnlyProperty,
            self._set_property_value,
            property_obj,
            FAKE_VALUE2,
        )
        self.assertEqual(property_obj._value, FAKE_VALUE)

    def test_set_value_if_id_property_and_value_is_same(self):
        property_obj = properties.IDProperty(
            self.positive_fake_property_type, value=FAKE_VALUE
        )

        self.assertIsNone(self._set_property_value(property_obj, FAKE_VALUE))
        self.assertEqual(property_obj._value, FAKE_VALUE)

    def test_set_value_if_id_property_and_value_is_different(self):
        property_obj = properties.IDProperty(
            self.positive_fake_property_type, value=FAKE_VALUE
        )

        self.assertRaises(
            exceptions.ReadOnlyProperty,
            self._set_property_value,
            property_obj,
            FAKE_VALUE2,
        )
        self.assertEqual(property_obj._value, FAKE_VALUE)

    def test_set_force_correct_value(self):
        property_obj = properties.Property(self.positive_fake_property_type)

        self.assertIsNone(property_obj.set_value_force(FAKE_VALUE))
        self.assertEqual(property_obj._value, FAKE_VALUE)
        self.positive_fake_property_type.validate.assert_called_with(
            FAKE_VALUE
        )

    def test_set_force_incorect_value(self):
        property_obj = properties.Property(self.negative_fake_property_type)
        old_value = property_obj._value

        self.assertRaises(
            exceptions.TypeError, property_obj.set_value_force, FAKE_VALUE
        )
        self.assertEqual(property_obj._value, old_value)
        self.negative_fake_property_type.validate.assert_called_with(
            FAKE_VALUE
        )

    def test_set_force_none_value(self):
        property_obj = properties.Property(
            self.positive_fake_property_type, required=True, value=FAKE_VALUE
        )
        old_value = property_obj._value

        self.assertRaises(
            exceptions.PropertyRequired, property_obj.set_value_force, None
        )
        self.assertEqual(property_obj._value, old_value)


class PropertyCreatorTestCase(base.BaseTestCase):

    ARGS = [1, 2, 3]
    KWARGS = {"fake_key1": "fake_value1", "fake_key2": "fake_value2"}

    def setUp(self):
        self.property_mock = mock.Mock(return_value=FAKE_VALUE)
        self.prop_type_mock = mock.Mock()
        self.test_instance = properties.PropertyCreator(
            self.property_mock, self.prop_type_mock, self.ARGS, self.KWARGS
        )

    def test_call_object(self):
        self.assertEqual(self.test_instance(FAKE_VALUE2), FAKE_VALUE)
        self.property_mock.assert_called_once_with(
            value=FAKE_VALUE2,
            property_type=self.prop_type_mock,
            *self.ARGS,
            **self.KWARGS
        )

    def test_get_property_class(self):
        self.assertEqual(
            self.test_instance.get_property_class(), self.property_mock
        )


class PropertyCollectionTestCase(base.BaseTestCase):

    def setUp(self):

        self.kwargs = {
            "fake1": mock.Mock(
                **{
                    "get_property_class.return_value": FAKE_VALUE,
                    "return_value": FAKE_VALUE2,
                }
            ),
            "fake2": mock.Mock(
                **{
                    "get_property_class.return_value": FAKE_VALUE2,
                    "return_value": FAKE_VALUE,
                }
            ),
        }
        self.test_instance = properties.PropertyCollection(**self.kwargs)

    def test_properties(self):
        self.assertEqual(self.test_instance.properties, self.kwargs)

    def test_change_properties_dict(self):
        def set_item(d, key, value):
            d[key] = value

        self.assertRaises(
            TypeError, set_item, self.test_instance.properties, "fake1", 2
        )

    def test_get_item_fake1(self):
        self.assertEqual(self.test_instance["fake1"], FAKE_VALUE)
        self.assertTrue(self.kwargs["fake1"].get_property_class.called)
        self.assertFalse(self.kwargs["fake2"].get_property_class.called)

    def test_get_item_fake2(self):
        self.assertEqual(self.test_instance["fake2"], FAKE_VALUE2)
        self.assertFalse(self.kwargs["fake1"].get_property_class.called)
        self.assertTrue(self.kwargs["fake2"].get_property_class.called)

    def test_instantiate_property_fake1(self):
        self.assertEqual(
            self.test_instance.instantiate_property(
                name="fake1", value=FAKE_VALUE3
            ),
            FAKE_VALUE2,
        )
        self.kwargs["fake1"].assert_called_once_with(FAKE_VALUE3)
        self.assertFalse(self.kwargs["fake2"].called)

    def test_instantiate_property_fake2(self):
        self.assertEqual(
            self.test_instance.instantiate_property(
                name="fake2", value=FAKE_VALUE3
            ),
            FAKE_VALUE,
        )
        self.kwargs["fake2"].assert_called_once_with(FAKE_VALUE3)
        self.assertFalse(self.kwargs["fake1"].called)

    def test_concatenate_two_collections(self):
        fake_property3 = mock.Mock()
        test_instance2 = properties.PropertyCollection(fake3=fake_property3)
        new_properties = self.kwargs
        new_properties["fake3"] = fake_property3

        res = self.test_instance + test_instance2
        self.assertIsInstance(res, properties.PropertyCollection)
        self.assertNotEqual(res, self.test_instance)
        self.assertNotEqual(res, test_instance2)
        self.assertEqual(res._properties, new_properties)

    def test_concatenate_collection_and_other_object(self):

        def concatenate(a, b):
            return a + b

        self.assertRaises(TypeError, concatenate, self.test_instance, object())


class PropertyManagerTestCase(base.BaseTestCase):

    def setUp(self):
        self.collection_mock = mock.Mock(
            **{
                "properties.items.return_value": [
                    ("fake1", "fake1"),
                    ("fake2", "fake2"),
                ],
                "instantiate_property.return_value": FAKE_VALUE,
            }
        )

    def test_init_manager(self):
        res = properties.PropertyManager(self.collection_mock)
        instantiate_property_calls = [
            mock.call("fake1", None),
            mock.call("fake2", None),
        ]

        self.assertIsInstance(res, properties.PropertyManager)
        self.collection_mock.instantiate_property.assert_has_calls(
            instantiate_property_calls, any_order=True
        )

    def test_init_manager_with_correct_kwargs(self):
        res = properties.PropertyManager(
            self.collection_mock, fake1=FAKE_VALUE2, fake2=FAKE_VALUE3
        )
        instantiate_property_calls = [
            mock.call("fake1", FAKE_VALUE2),
            mock.call("fake2", FAKE_VALUE3),
        ]

        self.assertIsInstance(res, properties.PropertyManager)
        self.collection_mock.instantiate_property.assert_has_calls(
            instantiate_property_calls, any_order=True
        )

    @base.unittest.skip("Checking of redundant data is turned off.")
    def test_init_manager_with_incorrect_kwargs(self):
        self.assertRaises(
            TypeError,
            properties.PropertyManager,
            self.collection_mock,
            fake3=FAKE_VALUE3,
        )

    def test_properties(self):
        property_manager = properties.PropertyManager(self.collection_mock)

        self.assertEqual(
            property_manager.properties,
            {"fake1": "FAKE_VALUE", "fake2": "FAKE_VALUE"},
        )

    def test_change_properties_dict(self):
        property_manager = properties.PropertyManager(self.collection_mock)

        def set_item(d, key, value):
            d[key] = value

        self.assertRaises(
            TypeError, set_item, property_manager.properties, "fake1", 2
        )


@mock.patch(
    "restalchemy.dm.properties.PropertyCreator", return_value=FAKE_VALUE
)
class PropertyFuncTestCase(base.BaseTestCase):

    ARGS = (1, 2, 3)
    KWARGS = {"fake_key1": "fake_value1", "fake_key2": "fake_value2"}

    def test_create_property(self, pc_mock):
        self.assertEqual(
            properties.property(*self.ARGS, **self.KWARGS), FAKE_VALUE
        )
        pc_mock.assert_called_once_with(
            prop_class=properties.Property,
            prop_type=1,
            args=self.ARGS[1:],
            kwargs=self.KWARGS,
        )

    def test_create_property_with_property_class(self, pc_mock):

        class LocalProperty(properties.AbstractProperty):

            @property
            def value(self):
                pass

            def set_value_force(self, value):
                pass

        self.assertEqual(
            properties.property(
                property_class=LocalProperty, *self.ARGS, **self.KWARGS
            ),
            FAKE_VALUE,
        )
        pc_mock.assert_called_once_with(
            prop_class=LocalProperty,
            prop_type=1,
            args=self.ARGS[1:],
            kwargs=self.KWARGS,
        )

    def test_create_property_with_incorect_property_class(self, pc_mock):
        self.assertRaises(
            ValueError,
            properties.property,
            property_class=object,
            *self.ARGS,
            **self.KWARGS
        )
