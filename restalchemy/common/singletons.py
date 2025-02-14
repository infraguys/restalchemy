# Copyright (c) 2014 Mirantis, Inc
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

import six
import threading


class MetaSingleton(type):
    """Meta Singleton

    For example py2:

    >>> class ConcreteSingleton:
    ...     __metaclass__ = MetaSingleton

    For example py3:

    >>> class ConcreteSingleton(metaclass=MetaSingleton):
    ...     pass

    For example py2 and py3:

    >>> @six.add_metaclass(MetaSingleton)
        class ConcreteSingleton(object):
    ...     pass
    """

    _instance = None
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(MetaSingleton, cls).__call__(
                        *args, **kwargs
                    )
        return cls._instance


@six.add_metaclass(MetaSingleton)
class InheritSingleton(object):
    """Inherit Singleton

    For example:

    >>> class ConcreteSingleton(InheritSingleton):
    ...     pass
    """

    pass
