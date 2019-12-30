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

import uuid

import sqlalchemy as sa
from sqlalchemy.ext import declarative

from restalchemy.dm import types

Base = declarative.declarative_base()


class VM(Base):
    __tablename__ = 'vms'

    uuid = sa.Column(sa.String(36), primary_key=True,
                     default=lambda: str(uuid.uuid4()))
    state = sa.Column(sa.String(10), nullable=False)
    name = sa.Column(sa.String(255), nullable=False)

    def __init__(self, name, state="off"):
        super(VM, self).__init__()
        self.name = name
        self.state = state

    @classmethod
    def get_model_type(cls):
        return cls

    @classmethod
    def get_id_property(cls):
        return {'uuid': types.String(min_length=32, max_length=32)}
