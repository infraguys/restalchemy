# Copyright (c) 2014 Eugene Frolov <efrolov@mirantis.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from oslo_config import cfg

from restalchemy import version


def parse(args):
    cfg.CONF(
        args=args,
        project="restalchemy",
        version="RESTAlchemy %s" % version.version_info.release_string(),
    )
    return cfg.CONF.config_file


class ConfigFileIsntDefined(Exception):
    pass


def parse_or_die(args=[]):
    if not parse(args):
        raise ConfigFileIsntDefined()


def parse_sys_args_or_die():
    return parse_or_die(sys.argv[1:])
