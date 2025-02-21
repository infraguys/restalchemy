# Copyright 2019 Eugene Frolov
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

from __future__ import absolute_import  # noqa

from mysql.connector import conversion


class MySQLConverter(conversion.MySQLConverter):

    def _list_to_mysql(self, value):
        """Convert list value to mysql driver type

        Convert value to list in for in operation in with statement.
        """
        return [self.to_mysql(item) for item in value]

    def escape(self, value, sql_mode=None):
        """Escape dangerous symbols in value

        Escapes special characters as they are expected to by when MySQL
        receives them.
        As found in MySQL source mysys/charset.c
        Returns the value if not a string, or the escaped string.
        """
        if isinstance(value, list):
            return [self.escape(item, sql_mode) for item in value]
        return super(MySQLConverter, self).escape(value, sql_mode)

    def quote(self, buf):
        """Quote all text values

        Quote the parameters for commands. General rules:
          o numbers are returns as bytes using ascii codec
          o None is returned as bytearray(b'NULL')
          o Everything else is single quoted '<buf>'
        Returns a bytearray object.
        """
        if isinstance(buf, list):
            tmp_list_buf = [self.quote(item) for item in buf]
            tmp_str_buf = b"(%s)" % (b", ".join(tmp_list_buf))
            return bytearray(tmp_str_buf)
        return super(MySQLConverter, self).quote(buf)

    _JSON_to_python = conversion.MySQLConverter._string_to_python

    def _BLOB_to_python(self, value, dsc=None):  # pylint: disable=C0103
        """Convert BLOB data type to Python."""
        if dsc is not None:
            if (
                dsc[7] & conversion.FieldFlag.BLOB
                and dsc[7] & conversion.FieldFlag.BINARY
            ):
                return bytes(value)
        return self._string_to_python(value, dsc)
