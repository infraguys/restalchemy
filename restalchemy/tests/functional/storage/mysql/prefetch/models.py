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

import mock

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.dm import types
from restalchemy.storage.sql import orm


# root table
FAKE_ROOT_INT = 0
FAKE_ROOT_STR = "root"
FAKE_ROOT_BOOL = True

# lnp1_1 table
FAKE_LNP1_1_INT = 11
FAKE_LNP1_1_STR = "lnp1_1"
FAKE_LNP1_1_BOOL = True

# lnp1_2 table
FAKE_LNP1_2_INT = 12
FAKE_LNP1_2_STR = "lnp1_2"
FAKE_LNP1_2_BOOL = True

# lwp1_1 table
FAKE_LWP1_1_INT = 111
FAKE_LWP1_1_STR = "lwp1_1"
FAKE_LWP1_1_BOOL = True

# lwp1_2 table
FAKE_LWP1_2_INT = 112
FAKE_LWP1_2_STR = "lwp1_2"
FAKE_LWP1_2_BOOL = True

# lwp2_1 table
FAKE_LWP2_1_INT = 21
FAKE_LWP2_1_STR = "lwp2_1"
FAKE_LWP2_1_BOOL = True

# lwp2_2 table
FAKE_LWP2_2_INT = 22
FAKE_LWP2_2_STR = "lwp2_2"
FAKE_LWP2_2_BOOL = True

# lwp2_3 table
FAKE_LWP2_3_INT = 23
FAKE_LWP2_3_STR = "lwp2_3"
FAKE_LWP2_3_BOOL = True

# lwp2_4 table
FAKE_LWP2_4_INT = 24
FAKE_LWP2_4_STR = "lwp2_4"
FAKE_LWP2_4_BOOL = True


# TODO(efrolov): convert to mock wrapper for handle all methods
OBJECT_COLLECTION_MOCK = mock.Mock(spec=orm.ObjectCollection)


class ObjectCollection(orm.ObjectCollection):

    def get_all(
        self,
        filters=None,
        session=None,
        cache=False,
        limit=None,
        order_by=None,
        locked=False,
    ):
        OBJECT_COLLECTION_MOCK.get_all(
            filters=filters,
            session=session,
            cache=cache,
            limit=limit,
            order_by=order_by,
            locked=locked,
        )
        return super(ObjectCollection, self).get_all(
            filters=filters,
            session=session,
            limit=limit,
            order_by=order_by,
            locked=locked,
        )


class SQLStorableMixin(orm.SQLStorableMixin):

    _ObjectCollection = ObjectCollection


class Root(models.ModelWithUUID, SQLStorableMixin):
    __tablename__ = "root"

    field_int = properties.property(types.Integer(), default=FAKE_ROOT_INT)
    field_str = properties.property(types.String(), default=FAKE_ROOT_STR)
    field_bool = properties.property(types.Boolean(), default=FAKE_ROOT_BOOL)


class LNP1_1(models.ModelWithUUID, SQLStorableMixin):
    __tablename__ = "lnp1_1"

    root = relationships.relationship(Root, required=True, prefetch=False)
    field_int = properties.property(types.Integer(), default=FAKE_LNP1_1_INT)
    field_str = properties.property(types.String(), default=FAKE_LNP1_1_STR)
    field_bool = properties.property(types.Boolean(), default=FAKE_LNP1_1_BOOL)


class LNP1_2(models.ModelWithUUID, SQLStorableMixin):
    __tablename__ = "lnp1_2"

    root = relationships.relationship(Root, required=False, prefetch=False)
    field_int = properties.property(types.Integer(), default=FAKE_LNP1_2_INT)
    field_str = properties.property(types.String(), default=FAKE_LNP1_2_STR)
    field_bool = properties.property(types.Boolean(), default=FAKE_LNP1_2_BOOL)


class LWP1_1(models.ModelWithUUID, SQLStorableMixin):
    __tablename__ = "lwp1_1"

    root = relationships.relationship(Root, required=True, prefetch=True)
    field_int = properties.property(types.Integer(), default=FAKE_LWP1_1_INT)
    field_str = properties.property(types.String(), default=FAKE_LWP1_1_STR)
    field_bool = properties.property(types.Boolean(), default=FAKE_LWP1_1_BOOL)


class LWP1_2(models.ModelWithUUID, SQLStorableMixin):
    __tablename__ = "lwp1_2"

    root = relationships.relationship(Root, required=False, prefetch=True)
    field_int = properties.property(types.Integer(), default=FAKE_LWP1_2_INT)
    field_str = properties.property(types.String(), default=FAKE_LWP1_2_STR)
    field_bool = properties.property(types.Boolean(), default=FAKE_LWP1_2_BOOL)


class LWP2_1(models.ModelWithUUID, SQLStorableMixin):
    __tablename__ = "lwp2_1"

    lwp1_1 = relationships.relationship(LWP1_1, required=True, prefetch=True)
    field_int = properties.property(types.Integer(), default=FAKE_LWP2_1_INT)
    field_str = properties.property(types.String(), default=FAKE_LWP2_1_STR)
    field_bool = properties.property(types.Boolean(), default=FAKE_LWP2_1_BOOL)


class LWP2_2(models.ModelWithUUID, SQLStorableMixin):
    __tablename__ = "lwp2_2"

    lwp1_1 = relationships.relationship(LWP1_1, required=False, prefetch=True)
    field_int = properties.property(types.Integer(), default=FAKE_LWP2_2_INT)
    field_str = properties.property(types.String(), default=FAKE_LWP2_2_STR)
    field_bool = properties.property(types.Boolean(), default=FAKE_LWP2_2_BOOL)


class LWP2_3(models.ModelWithUUID, SQLStorableMixin):
    __tablename__ = "lwp2_3"

    lwp1_2 = relationships.relationship(LWP1_2, required=True, prefetch=True)
    field_int = properties.property(types.Integer(), default=FAKE_LWP2_3_INT)
    field_str = properties.property(types.String(), default=FAKE_LWP2_3_STR)
    field_bool = properties.property(types.Boolean(), default=FAKE_LWP2_3_BOOL)


class LWP2_4(models.ModelWithUUID, SQLStorableMixin):
    __tablename__ = "lwp2_4"

    lwp1_2 = relationships.relationship(LWP1_2, required=False, prefetch=True)
    field_int = properties.property(types.Integer(), default=FAKE_LWP2_4_INT)
    field_str = properties.property(types.String(), default=FAKE_LWP2_4_STR)
    field_bool = properties.property(types.Boolean(), default=FAKE_LWP2_4_BOOL)
