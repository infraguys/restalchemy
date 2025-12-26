# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
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

import re

from restalchemy.common import exceptions


class RecordNotFound(exceptions.RestAlchemyException):

    code = 404
    message = (
        "Can't found record in storage for model (%(model)s) and "
        "filters (%(filters)s)."
    )


class MultipleUpdatesDetected(exceptions.RestAlchemyException):

    message = "Multiple records were updated in storage for %(model)s"


class HasManyRecords(exceptions.RestAlchemyException):

    message = (
        "Has many records in storage for model (%(model)s) and filters "
        "(%(filters)s)."
    )


class DeadLock(exceptions.RestAlchemyException):

    message = (
        "Deadlock found when trying to get lock. " "Original message: %(msg)s"
    )


class ConflictRecords(exceptions.RestAlchemyException):

    code = 409
    message = "Duplicate parameters for '%(model)s'. Original message: %(msg)s"

    def __init__(self, **kwargs):
        super(ConflictRecords, self).__init__(**kwargs)
        self._original_msg = kwargs.get("msg") or ""

    def _re_parser(self, re_template):
        result = re.search(re_template, self._original_msg)
        if result is None:
            raise ValueError(
                f"Incorrect message for parsing. {self._original_msg}"
                f" but should be {re_template}"
            )
        return result.groups()

    @property
    def _parsed_message_mysql(self):
        re_template = r"Duplicate entry '(.*)' for key '(.*)'"
        result = self._re_parser(re_template)
        return {
            "key": result[1],
            "value": result[0],
        }

    @property
    def _parsed_message_postgresql(self):
        re_template = r"DETAIL:\s+Key \((\w+)\)=\(([^)]+)\)"
        result = self._re_parser(re_template)
        return {
            "key": result[0],
            "value": result[1],
        }

    @property
    def _parse_message(self):
        if self._original_msg.startswith("Duplicate entry"):
            return self._parsed_message_mysql
        elif self._original_msg.startswith("duplicate key value violates"):
            return self._parsed_message_postgresql
        raise ValueError(f"Can't parse message: {self._original_msg}")

    @property
    def value(self):
        return self._parse_message["value"]

    @property
    def key(self):
        return self._parse_message["key"]


class UnknownStorageException(exceptions.RestAlchemyException):
    message = "Unknown storage exception: %(caused)r"

    def __init__(self, caused, **kwargs):
        self._caused = caused
        super(UnknownStorageException, self).__init__(caused=caused, **kwargs)

    @property
    def caused(self):
        return self._caused
