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

from restalchemy.common import contexts
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import orm
from restalchemy.storage.sql import sessions


# CREATE TABLE `foos` (
#      `uuid` CHAR(36) CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL ,
#      `foo_field1` INT NOT NULL ,
#      `foo_field2` VARCHAR(255) NOT NULL ,
# PRIMARY KEY (`uuid`(36)) USING HASH)
# ENGINE = InnoDB;
class FooModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "foos"
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


# One must set name 'default' for default storage if you want to work with
# storage operations without session parameter.
engines.engine_factory.configure_factory(
    db_url="mysql://user:password@127.0.0.1:3306/test",
    name="default",  # name argument by default is 'default' and can be skipped
)

# db_one engine is not equal default engine because it has separate connection
# pool therefore session from default engine is not equal session from
# db_one engine. But if you use thread storage sessions any storage operations
# will working with session from thread storage by default.
engines.engine_factory.configure_factory(
    db_url="mysql://user:password@127.0.0.1:3306/test",
    name="db_one",  # by default name is 'default'
)
engines.engine_factory.configure_factory(
    db_url="mysql://user:password@127.0.0.1:3307/test",
    name="db_two",  # by default name is 'default'
)

engine_one = engines.engine_factory.get_engine("db_one")
engine_two = engines.engine_factory.get_engine("db_two")

session_one = engine_one.get_session()
session_two = engine_two.get_session()

foo_one = FooModel(foo_field1=1)
foo_one.insert(session=session_one)
session_one.commit()


foo_two = FooModel(foo_field1=2)
foo_two.insert(session=session_two)
session_two.commit()

with engine_two.session_manager() as session:

    # Incorrect. Session from context manager is not used because new session
    # from default storage going to create in get_all call. And you get data
    # from default database (engine).
    #
    # the result: [<FooModel {foo_field1: 1,
    #                         uuid: 27ce96dc-daad-4272-88d8-8e41028c38e9,
    #                         foo_field2: foo_str}>]
    print("Incorrect input for storage two:")
    print(FooModel.objects.get_all())

    # correct call
    # the result: [<FooModel {foo_field1: 2,
    #                         uuid: 78141610-6709-4296-bd56-7c62aec97aa8,
    #                         foo_field2: foo_str} >]
    print("Correct input for storage two:")
    print(FooModel.objects.get_all(session=session))


# The next expressions is correct
context_two = contexts.Context(engine_name="db_two")
with context_two.session_manager() as session:
    print("Correct input for storage two for context session:")
    print(FooModel.objects.get_all())


# But you can not create two active session from context
context_one = contexts.Context(engine_name="db_one")
with context_two.session_manager() as session_2:

    try:
        with context_one.session_manager() as session_1:
            print("Newer call")
    except sessions.SessionConflict as e:
        print("Session conflict:", e)
