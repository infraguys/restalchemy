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

import uuid

import mock

from restalchemy.common import exceptions
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.dm import types
from restalchemy.tests.unit import base


class FakeProperty(mock.Mock):
    pass


FAKE_PROPERTY1 = FakeProperty()
FAKE_PROPERTY2 = FakeProperty()
FAKE_VALUE1 = "Fake value 1"


class MetaModelTestCase(base.BaseTestCase):

    with mock.patch("restalchemy.dm.properties.PropertyCreator", FakeProperty):

        class Model(object, metaclass=models.MetaModel):

            fake_prop1 = FAKE_PROPERTY1
            fake_prop2 = FAKE_PROPERTY2

    def test_model_class(self):
        self.assertIsInstance(
            self.Model.properties, properties.PropertyCollection
        )

    def test_metamodel_getattr(self):
        self.assertNotEqual(self.Model.fake_prop1, FAKE_PROPERTY1)
        self.assertNotEqual(self.Model.fake_prop2, FAKE_PROPERTY2)

    def test_metamodel_getattr_raises_attribute_error(self):
        self.assertRaises(AttributeError, lambda: self.Model.fake_prop3)


class ModelTestCase(base.BaseTestCase):

    PM_MOCK = mock.MagicMock(name="PropertyManager object")

    @mock.patch(
        "restalchemy.dm.properties.PropertyManager", return_value=PM_MOCK
    )
    def setUp(self, pm_mock):
        super(ModelTestCase, self).setUp()
        self.PM_MOCK.__getitem__.side_effect = None
        self.PM_MOCK.reset_mock()
        self.pm_mock = pm_mock
        self.kwargs = {"kwarg1": 1, "kwarg2": 2}
        self.test_instance = models.Model(**self.kwargs)
        self.test_instance.validate = mock.MagicMock()

    def test_validate_call(self):
        models.Model.validate = mock.MagicMock()
        test_instance = models.Model(**self.kwargs)
        test_instance.validate.assert_called_once_with()

    def test_obj(self):
        self.assertEqual(self.test_instance.properties, self.PM_MOCK)
        self.pm_mock.assert_called_once_with(
            models.Model.properties, **self.kwargs
        )

    def test_obj_getattr(self):
        self.assertEqual(
            self.test_instance.fake_prop1, self.PM_MOCK["fake_prop1"].value
        )

    def test_obj_getattr_raise_attribute_error(self):
        self.PM_MOCK.__getitem__.side_effect = KeyError

        self.assertRaises(
            AttributeError, lambda: self.test_instance.fake_prop1
        )

    def test_obj_setattr(self):
        self.test_instance.fake_prop1 = FAKE_VALUE1

        self.assertEqual(self.PM_MOCK.__getitem__().value, FAKE_VALUE1)


class Model1(models.Model):
    pass


class Model2(models.Model):
    pass


class Model3(models.ModelWithUUID):
    pass


class BaseModel(models.Model):

    property1 = properties.property(types.Integer())
    property2 = properties.property(types.Integer())
    property3 = relationships.relationship(Model1)
    property4 = relationships.relationship(Model2)


class FakeModel(BaseModel):
    property1 = properties.property(types.String())
    property3 = relationships.relationship(Model3)


class SimpleViewModel(models.ModelWithUUID, models.SimpleViewMixin):
    int_property = properties.property(types.Integer(), default=1)
    str_property = properties.property(types.String(), default="foo")
    none_property = properties.property(
        types.AllowNone(types.Integer()), default=None
    )


class InheritModelTestCase(base.BaseTestCase):

    def test_correct_type_in_base_model(self):
        props = BaseModel.properties.properties

        self.assertIsInstance(props["property1"]._property_type, types.Integer)
        self.assertIsInstance(props["property2"]._property_type, types.Integer)
        self.assertEqual(props["property3"]._property_type, Model1)
        self.assertEqual(props["property4"]._property_type, Model2)

    def test_correct_type_in_inherit_model(self):
        props = FakeModel.properties.properties

        self.assertIsInstance(props["property1"]._property_type, types.String)
        self.assertIsInstance(props["property2"]._property_type, types.Integer)
        self.assertEqual(props["property3"]._property_type, Model3)
        self.assertEqual(props["property4"]._property_type, Model2)


class DirtyModelTestCase(base.BaseTestCase):

    def setUp(self):
        super(DirtyModelTestCase, self).setUp()
        self._model = FakeModel(
            property1="fake_string",
            property2=2,
            property3=Model3(),
            property4=Model2(),
        )

    def test_dirty_is_false(self):
        self.assertFalse(self._model.is_dirty())

    def test_dirty_is_false_after_change_property2(self):
        self._model.property2 = 6
        self._model.property2 = 2

        self.assertFalse(self._model.is_dirty())

    def test_property1_is_dirty(self):
        self._model.property1 = "new fake_string"

        self.assertTrue(self._model.is_dirty())

    def test_property3_is_dirty(self):
        self._model.property3 = Model3()

        self.assertTrue(self._model.is_dirty())

    def test_property3_is_not_dirty(self):
        self._model.property3 = Model3(uuid=self._model.property3.uuid)

        self.assertFalse(self._model.is_dirty())


class FakeModelWithID(BaseModel):
    uuid = properties.property(types.UUID(), id_property=True)
    property3 = relationships.relationship(Model3)


class FakeModelWithSeveralIDs(BaseModel):
    uuid = properties.property(types.UUID(), id_property=True)
    uuid2 = properties.property(types.UUID(), id_property=True)
    property3 = relationships.relationship(Model3)


class ModelWithIDsTestCase(base.BaseTestCase):

    def test_get_id_property(self):
        props = FakeModelWithID.properties.properties

        self.assertEqual(
            FakeModelWithID.get_id_property(), {"uuid": props["uuid"]}
        )
        with self.assertRaises(TypeError):
            FakeModelWithSeveralIDs.get_id_property()

    def test_get_id_property_name(self):
        self.assertEqual(FakeModelWithID.get_id_property_name(), "uuid")
        with self.assertRaises(TypeError):
            FakeModelWithSeveralIDs.get_id_property_name()

    def test_model_plain_dict(self):
        fakeInt = 1
        fakeUUID1 = uuid.uuid4()
        fakeUUID2 = uuid.uuid4()
        fakeUUID3 = uuid.uuid4()

        model = FakeModelWithID(
            uuid=fakeUUID1,
            property1=fakeInt,
            property2=fakeInt,
            property3=Model3(uuid=fakeUUID2),
            property4=Model2(),
        )

        expected = {
            "uuid": fakeUUID1,
            "property1": fakeInt,
            "property2": fakeInt,
            "property3": fakeUUID2,
            "property4": None,
        }

        plain_dict = model.as_plain_dict()
        self.assertEqual(plain_dict, expected)

        # dictionary changes do not affect model
        plain_dict["property3"] = Model3(uuid=fakeUUID3)
        self.assertEqual(model.property3.uuid, fakeUUID2)


class ModelWithRequiredUUIDTestCase(base.BaseTestCase):

    def test_uuid_provided(self):
        model_uuid = uuid.uuid4()

        model = models.ModelWithRequiredUUID(uuid=model_uuid)

        self.assertEqual(model_uuid, model.uuid)

    def test_uuid_not_provided(self):
        self.assertRaises(
            exceptions.PropertyRequired, models.ModelWithRequiredUUID
        )

    def test_uuid_is_readonly(self):
        uuid_1 = uuid.uuid4()
        uuid_2 = uuid.uuid4()

        model = models.ModelWithRequiredUUID(uuid=uuid_1)

        with self.assertRaises(exceptions.ReadOnlyProperty):
            model.uuid = uuid_2

    def test_get_model_id(self):
        uuid_1 = uuid.uuid4()

        model = models.ModelWithRequiredUUID(uuid=uuid_1)

        self.assertEqual(model.get_id(), uuid_1)


class SimpleViewMixinTestCase(base.BaseTestCase):

    def test_dump_to_simple_view(self):
        simple_view_model = SimpleViewModel()
        view = simple_view_model.dump_to_simple_view()

        self.assertEqual(view["int_property"], 1)
        self.assertEqual(view["str_property"], "foo")
        self.assertIs(view["none_property"], None)
        self.assertIsInstance(view["uuid"], str)

    def test_restore_to_simple_view(self):
        simple_view_model = SimpleViewModel()
        view = {
            "uuid": "2e39d8df-2662-4834-ad86-c637d1edd504",
            "int_property": 2,
            "str_property": "bar",
            "none_property": None,
        }
        simple_view_model = SimpleViewModel.restore_from_simple_view(**view)

        self.assertEqual(simple_view_model.int_property, 2)
        self.assertEqual(simple_view_model.str_property, "bar")
        self.assertIs(simple_view_model.none_property, None)
        self.assertIs(simple_view_model.uuid.__class__, uuid.UUID)
