# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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


from restalchemy.common import exceptions


class RecordNotFound(exceptions.RestAlchemyException):

    message = ("Can't found record in storage for model (%(model)s) and "
               "filters (%(filters)s).")


class MultipleUpdatesDetected(exceptions.RestAlchemyException):

    message = "Multiple records were updated in storage for %(model)s"


class HasManyRecords(exceptions.RestAlchemyException):

    message = ("Has many records in storage for model (%(model)s) and filters "
               "(%(filters)s).")


class ConflictRecords(exceptions.RestAlchemyException):
    message = "Duplicate parameters for '%(model)s'. Original message: %(msg)s"


class UnknownStorageException(exceptions.RestAlchemyException):
    message = "Unknown storage exception: %(caused)r"

    def __init__(self, caused, **kwargs):
        self._caused = caused
        super(UnknownStorageException, self).__init__(caused=caused, **kwargs)

    @property
    def caused(self):
        return self._caused
