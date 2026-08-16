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
        self.positive_fake_property_type.validate.assert_called_with(FAKE_VALUE)

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
        self.positive_fake_property_type.validate.assert_called_with(FAKE_VALUE)

    def test_init_default_callable_value(self):
        property_obj = properties.Property(
            self.positive_fake_property_type, default=lambda: FAKE_VALUE
        )

        self.assertEqual(property_obj.value, FAKE_VALUE)
        self.positive_fake_property_type.validate.assert_called_with(FAKE_VALUE)

    def test_init_default_value_if_property_read_only(self):
        property_obj = properties.Property(
            self.positive_fake_property_type,
            default=FAKE_VALUE,
            read_only=True,
        )

        self.assertEqual(property_obj._value, FAKE_VALUE)
        self.positive_fake_property_type.validate.assert_called_with(FAKE_VALUE)

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
        self.positive_fake_property_type.validate.assert_called_with(FAKE_VALUE)

    def test_init_none_value(self):
        property_obj = properties.Property(self.negative_fake_property_type, value=None)

        self.assertEqual(property_obj._value, None)

    def test_init_value_with_read_only(self):
        property_obj = properties.Property(
            self.positive_fake_property_type, read_only=True, value=FAKE_VALUE2
        )

        self.assertEqual(property_obj._value, FAKE_VALUE2)
        self.positive_fake_property_type.validate.assert_called_with(FAKE_VALUE2)

    def test_set_correct_value(self):
        property_obj = properties.Property(self.positive_fake_property_type)

        self.assertIsNone(self._set_property_value(property_obj, FAKE_VALUE))
        self.assertEqual(property_obj._value, FAKE_VALUE)
        self.positive_fake_property_type.validate.assert_called_with(FAKE_VALUE)

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
        self.negative_fake_property_type.validate.assert_called_with(FAKE_VALUE)

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
        self.positive_fake_property_type.validate.assert_called_with(FAKE_VALUE)

    def test_set_force_incorect_value(self):
        property_obj = properties.Property(self.negative_fake_property_type)
        old_value = property_obj._value

        self.assertRaises(
            exceptions.TypeError, property_obj.set_value_force, FAKE_VALUE
        )
        self.assertEqual(property_obj._value, old_value)
        self.negative_fake_property_type.validate.assert_called_with(FAKE_VALUE)

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
            **self.KWARGS,
        )

    def test_get_property_class(self):
        self.assertEqual(self.test_instance.get_property_class(), self.property_mock)


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
            self.test_instance.instantiate_property(name="fake1", value=FAKE_VALUE3),
            FAKE_VALUE2,
        )
        self.kwargs["fake1"].assert_called_once_with(FAKE_VALUE3)
        self.assertFalse(self.kwargs["fake2"].called)

    def test_instantiate_property_fake2(self):
        self.assertEqual(
            self.test_instance.instantiate_property(name="fake2", value=FAKE_VALUE3),
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
                # Neither name holds a nested collection.
                "nested_names": frozenset(),
                # Its items are doubles, not creators, so a model of it
                # cannot keep bare values.
                "values_can_stand_alone": False,
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

        self.assertRaises(TypeError, set_item, property_manager.properties, "fake1", 2)


@mock.patch("restalchemy.dm.properties.PropertyCreator", return_value=FAKE_VALUE)
class PropertyFuncTestCase(base.BaseTestCase):
    ARGS = (1, 2, 3)
    KWARGS = {"fake_key1": "fake_value1", "fake_key2": "fake_value2"}

    def test_create_property(self, pc_mock):
        self.assertEqual(properties.property(*self.ARGS, **self.KWARGS), FAKE_VALUE)
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
            **self.KWARGS,
        )


class PropertyCreatorBuildsTestCase(base.BaseTestCase):
    """What a creator builds, on the short path and off it.

    A creator answers everything a declaration settles once, and builds
    the property from there; the two paths must not disagree about
    defaults, validation or what counts as dirty.
    """

    def test_a_value_beats_the_default(self):
        creator = properties.property(types.String(), default="d")

        self.assertEqual("v", creator("v").value)
        self.assertEqual("d", creator(None).value)

    def test_a_callable_default_is_called_per_property(self):
        creator = properties.property(types.TypedList(types.String()), default=list)

        first, second = creator(None), creator(None)
        first.value.append("x")

        self.assertEqual(["x"], first.value)
        self.assertEqual([], second.value)

    def test_a_mutable_property_notices_it_was_changed(self):
        creator = properties.property(
            types.TypedList(types.String()), default=list, mutable=True
        )

        prop = creator(None)
        prop.value.append("x")

        self.assertEqual([], prop.old_value)
        self.assertTrue(prop.is_dirty())

    def test_a_value_of_the_wrong_type_is_refused(self):
        creator = properties.property(types.String())

        self.assertRaises(exceptions.TypeError, creator, 1)

    def test_a_required_property_without_a_value_is_refused(self):
        creator = properties.required_property(types.String())

        self.assertRaises(exceptions.PropertyRequired, creator, None)

    def test_a_read_only_property_keeps_its_flags(self):
        prop = properties.readonly_property(types.String())("v")

        self.assertTrue(prop.is_read_only())
        self.assertTrue(prop.is_required())
        self.assertRaises(exceptions.ReadOnlyProperty, setattr, prop, "value", "o")

    def test_an_id_property_says_so(self):
        prop = properties.property(types.String(), id_property=True)("v")

        self.assertIsInstance(prop, properties.IDProperty)
        self.assertTrue(prop.is_id_property())

    def test_a_property_class_of_its_own_is_built_as_before(self):
        class LocalProperty(properties.Property):
            pass

        prop = properties.property(
            types.String(), property_class=LocalProperty, default="d"
        )(None)

        self.assertIsInstance(prop, LocalProperty)
        self.assertEqual("d", prop.value)

    def test_the_example_is_carried_over(self):
        prop = properties.property(types.String(), example="e")(None)

        self.assertEqual("e", prop.example())

    def test_a_type_that_is_not_one_is_refused_at_declaration(self):
        self.assertRaises(TypeError, properties.property, object())


class PropertyCreatorPathsAgreeTestCase(base.BaseTestCase):
    """The short path must build what the constructor would.

    A creator answers everything a declaration settles and fills the
    property in itself, which is a second place that knows what a
    property is made of. This is what keeps the two from drifting: the
    objects have to come out indistinguishable, down to the attributes
    they carry.
    """

    DECLARATIONS = (
        ("plain", types.String(), {}),
        ("default", types.String(), {"default": "d"}),
        ("callable default", types.TypedList(types.String()), {"default": list}),
        ("required", types.String(), {"required": True}),
        ("read only", types.String(), {"read_only": True}),
        (
            "mutable",
            types.TypedList(types.String()),
            {"default": list, "mutable": True},
        ),
        ("example", types.String(), {"example": "e"}),
        ("id", types.String(), {"id_property": True}),
        (
            "everything",
            types.TypedList(types.String()),
            {
                "default": list,
                "required": True,
                "read_only": True,
                "mutable": True,
                "example": ["e"],
            },
        ),
    )

    VALUES = (None, "v", ["v"])

    def test_both_paths_build_the_same_property(self):
        for label, prop_type, kwargs in self.DECLARATIONS:
            creator = properties.property(prop_type, **kwargs)
            constructor_kwargs = dict(kwargs)
            property_class = (
                properties.IDProperty
                if constructor_kwargs.pop("id_property", False)
                else properties.Property
            )
            for value in self.VALUES:
                fast = self._build(creator, value)
                slow = self._build(
                    lambda v: property_class(
                        property_type=prop_type, value=v, **constructor_kwargs
                    ),
                    value,
                )

                self.assertEqual(
                    type(fast).__name__,
                    type(slow).__name__,
                    "%s / %r" % (label, value),
                )
                if isinstance(fast, Exception) or isinstance(slow, Exception):
                    self.assertEqual(repr(fast), repr(slow), "%s / %r" % (label, value))
                    continue
                self.assertEqual(vars(fast), vars(slow), "%s / %r" % (label, value))
                self.assertEqual(
                    (
                        fast.value,
                        fast.old_value,
                        fast.is_dirty(),
                        fast.is_required(),
                        fast.is_read_only(),
                        fast.is_id_property(),
                        fast.example(),
                    ),
                    (
                        slow.value,
                        slow.old_value,
                        slow.is_dirty(),
                        slow.is_required(),
                        slow.is_read_only(),
                        slow.is_id_property(),
                        slow.example(),
                    ),
                    "%s / %r" % (label, value),
                )

    @staticmethod
    def _build(build, value):
        try:
            return build(value)
        except Exception as error:
            return error


class ValuesStandingAloneTestCase(base.BaseTestCase):
    """A model keeping values must be the model it would have been.

    Everything a property object answers -- its value, what it held to
    begin with, whether it may be written, whether it has changed -- has
    to come out the same whether the object was built when the model was
    or when something first asked for it.
    """

    def _collection(self, **declarations):
        return properties.PropertyCollection(**declarations)

    def test_a_value_given_as_none_is_a_value_nobody_gave(self):
        # What a stored NULL arrives as, and what the property
        # constructor has always done with it.
        collection = self._collection(
            name=properties.property(types.String(), default="d"),
            count=properties.property(types.Integer(), default=1),
        )

        manager = properties.PropertyManager(collection, name=None, count=None)

        self.assertEqual({"name": "d", "count": 1}, manager._values)

    def test_a_plain_declaration_keeps_its_values(self):
        collection = self._collection(
            name=properties.property(types.String(), default="d"),
            count=properties.property(types.Integer(), default=1),
        )

        manager = properties.PropertyManager(collection, name="n")

        self.assertEqual({"name": "n", "count": 1}, manager._values)
        self.assertEqual({}, manager._properties)

    def test_a_property_of_its_own_is_built_as_it_was(self):
        class LocalProperty(properties.Property):
            pass

        collection = self._collection(
            name=properties.property(
                types.String(), property_class=LocalProperty, default="d"
            ),
        )

        manager = properties.PropertyManager(collection)

        self.assertEqual({}, manager._values)
        self.assertIsInstance(manager._properties["name"], LocalProperty)

    def test_asking_for_one_builds_that_one(self):
        collection = self._collection(
            name=properties.property(types.String(), default="d"),
            count=properties.property(types.Integer(), default=1),
        )
        manager = properties.PropertyManager(collection)

        prop = manager["name"]

        self.assertIsInstance(prop, properties.Property)
        self.assertEqual("d", prop.value)
        self.assertNotIn("name", manager._values)
        self.assertIn("count", manager._values)

    def test_what_it_answers_does_not_depend_on_when_it_was_built(self):
        declarations = {
            "name": properties.property(types.String(), default="d"),
            "readonly": properties.readonly_property(types.String()),
            "identifier": properties.property(types.String(), id_property=True),
            "tags": properties.property(
                types.TypedList(types.String()), default=list, mutable=True
            ),
        }
        values = {"readonly": "r", "identifier": "i"}

        early = properties.PropertyManager(self._collection(**declarations), **values)
        early.materialise_all()
        late = properties.PropertyManager(self._collection(**declarations), **values)

        for name in declarations:
            self.assertEqual(self._facts(early[name]), self._facts(late[name]), name)

    def test_a_value_changed_in_place_is_still_noticed(self):
        collection = self._collection(
            tags=properties.property(
                types.TypedList(types.String()), default=list, mutable=True
            ),
        )
        manager = properties.PropertyManager(collection)

        manager.get_value("tags").append("x")

        self.assertEqual([], manager["tags"].old_value)
        self.assertTrue(manager["tags"].is_dirty())

    def test_walking_the_mapping_hands_over_properties(self):
        collection = self._collection(
            name=properties.property(types.String(), default="d"),
            count=properties.property(types.Integer(), default=1),
        )
        manager = properties.PropertyManager(collection)

        walked = dict(manager.items())

        self.assertEqual({"name", "count"}, set(walked))
        for prop in walked.values():
            self.assertIsInstance(prop, properties.Property)
        self.assertEqual({}, manager._values)

    def test_the_mapping_answers_the_same_before_and_after(self):
        collection = self._collection(
            name=properties.property(types.String(), default="d"),
            count=properties.property(types.Integer(), default=1),
        )
        manager = properties.PropertyManager(collection)

        self.assertEqual(2, len(manager))
        self.assertIn("name", manager)
        self.assertEqual({"name", "count"}, set(iter(manager)))
        self.assertEqual({"name": "d", "count": 1}, manager.value)
        manager.materialise_all()
        self.assertEqual(2, len(manager))
        self.assertIn("name", manager)
        self.assertEqual({"name", "count"}, set(iter(manager)))
        self.assertEqual({"name": "d", "count": 1}, manager.value)

    @staticmethod
    def _facts(prop):
        return (
            type(prop).__name__,
            prop.value,
            prop.old_value,
            prop.is_dirty(),
            prop.is_required(),
            prop.is_read_only(),
            prop.is_id_property(),
            prop.get_property_type(),
        )

    def test_nothing_written_to_is_nothing_changed(self):
        collection = self._collection(
            name=properties.property(types.String(), default="d"),
            tags=properties.property(
                types.TypedList(types.String()), default=list, mutable=True
            ),
        )
        manager = properties.PropertyManager(collection)

        # Answered without building a single property object.
        self.assertFalse(manager.is_dirty())
        self.assertEqual({}, manager._properties)

    def test_a_write_is_a_change_however_it_arrived(self):
        collection = self._collection(
            name=properties.property(types.String(), default="d"),
            tags=properties.property(
                types.TypedList(types.String()), default=list, mutable=True
            ),
        )

        written = properties.PropertyManager(collection)
        written["name"].value = "other"
        in_place = properties.PropertyManager(collection)
        in_place.get_value("tags").append("x")

        self.assertTrue(written.is_dirty())
        self.assertTrue(in_place.is_dirty())


class SharedEmptyMappingsTestCase(base.BaseTestCase):
    """The mapping a manager stands in with must stay empty.

    It is a class attribute shared by every manager there is, so a write
    that lands in it instead of in a mapping of the manager's own is
    every model's first value, not that model's.
    """

    def setUp(self):
        super(SharedEmptyMappingsTestCase, self).setUp()
        self._collection = properties.PropertyCollection(
            name=properties.property(types.String(), default="d"),
            tags=properties.property(
                types.TypedList(types.String()), default=list, mutable=True
            ),
        )

    def _assert_shared_are_empty(self):
        self.assertEqual({}, properties.PropertyManager._first_values)

    def test_pouring_values_writes_neither(self):
        manager = properties.PropertyManager(self._collection, name="n")

        self.assertEqual("n", manager.get_value("name"))
        self._assert_shared_are_empty()

    def test_building_a_property_writes_a_mapping_of_its_own(self):
        manager = properties.PropertyManager(self._collection, name="n")

        self.assertEqual("n", manager["name"].value)
        self.assertEqual(["name"], list(manager._properties))
        self._assert_shared_are_empty()

    def test_two_managers_do_not_see_each_other(self):
        first = properties.PropertyManager(self._collection, name="one")
        second = properties.PropertyManager(self._collection, name="two")

        first["name"]
        second["name"]

        self.assertEqual("one", first["name"].value)
        self.assertEqual("two", second["name"].value)
        self._assert_shared_are_empty()

    def test_a_declaration_that_cannot_stand_alone_writes_its_own(self):
        nested = properties.PropertyCollection(
            inner=properties.property(types.String(), default="d"),
        )
        collection = properties.PropertyCollection(
            name=properties.property(types.String(), default="d"),
            nested=nested,
        )

        manager = properties.PropertyManager(collection)

        self.assertEqual(["name", "nested"], sorted(manager._properties))
        self._assert_shared_are_empty()
