# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#    Copyright 2021 Eugene Frolov.
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

from restalchemy.dm import filters
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import orm


# CREATE TABLE `foos` (
#      `uuid` CHAR(36) CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL ,
#      `foo_field1` INT NOT NULL ,
#      `foo_field2` VARCHAR(255) NOT NULL ,
# PRIMARY KEY (`uuid`(36)) USING HASH)
# ENGINE = InnoDB;
class FooModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "foos"
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="field2_value")


engines.engine_factory.configure_factory(
    db_url="mysql://root:21070809d@127.0.0.1/test",
)


model1 = FooModel(foo_field1=10, foo_field2="Value1")
model2 = FooModel(foo_field1=20, foo_field2="Value2")
model3 = FooModel(foo_field1=30, foo_field2="TypeA")
model1.save()
model2.save()
model3.save()

print(FooModel.objects.count())
print(FooModel.objects.count(filters={"foo_field1": filters.GT(10)}))
print(FooModel.objects.count(filters={"foo_field2": "TypeA"}))

for model in FooModel.objects.get_all():
    model.delete()
