# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#    Copyright 2019 Eugene Frolov.
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

import uuid

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import orm


# CREATE TABLE `foos` (
#      `uuid` CHAR(36) CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL ,
#      `foo_field1` INT NOT NULL ,
#      `foo_field2` VARCHAR(255) NOT NULL ,
# PRIMARY KEY (`uuid`(36), `foo_field1`) USING HASH)
# ENGINE = InnoDB;
class FooModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "foos"
    foo_field1 = properties.property(
        types.Integer(),
        required=True,
        id_property=True,
    )
    foo_field2 = properties.property(types.String(), default="foo_str")


engines.engine_factory.configure_factory(
    db_url="mysql://root:21070809d@127.0.0.1/test",
)


model_uuid = uuid.uuid4()

model1 = FooModel(uuid=model_uuid, foo_field1=1, foo_field2="Model1")
model2 = FooModel(uuid=model_uuid, foo_field1=2, foo_field2="Model2")
model3 = FooModel(uuid=model_uuid, foo_field1=3, foo_field2="Model3")

model1.insert()
model2.insert()
model3.insert()

print(list(FooModel.objects.get_all()))

with engines.engine_factory.get_engine().session_manager() as session:
    session.batch_delete([model1, model2, model3])

print(list(FooModel.objects.get_all()))
