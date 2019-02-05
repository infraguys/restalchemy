# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2018 Mail.ru Group
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

from six.moves.urllib import parse as urllib


def force_last_slash(path):
    return path if path[-1] == '/' else path + '/'


def build_collection_uri(endpoint, uri):
    return urllib.urljoin(endpoint, force_last_slash(uri))


def build_resource_uri(endpoint, uri):
    return urllib.urljoin(endpoint, uri)
