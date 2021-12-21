# coding=utf-8
#
#    Copyright 2021 George Melikov.
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

import unittest

from restalchemy.dm import types_network


class RecordNameTestCase(unittest.TestCase):

    def setUp(self):
        super(RecordNameTestCase, self).setUp()
        self.test_instance = types_network.RecordName()

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance.validate('ns1.ra.restalchemy.com'))
        self.assertTrue(self.test_instance.validate('ns1.55.restalchemy.com'))
        self.assertTrue(self.test_instance.validate('n_s1.55.restalchemy.com'))
        self.assertTrue(self.test_instance.validate('n-1.55.restalchemy.com'))
        self.assertTrue(self.test_instance.validate('restalchemy.com'))
        self.assertTrue(self.test_instance.validate('a.b.c.d.1.2.3'))
        self.assertTrue(self.test_instance.validate('qa-auto-dnsidxbs'))

    def test_from_simple_type(self):
        self.assertEqual(self.test_instance.from_simple_type('.x.'), '.x')
        self.assertEqual(self.test_instance.from_simple_type('.x.x.'), '.x.x')
        self.assertEqual(self.test_instance.from_simple_type('@'), '')

    def test_to_simple_type(self):
        self.assertEqual(self.test_instance.to_simple_type(''), '@')
        self.assertEqual(self.test_instance.to_simple_type('xxx'), 'xxx')

    def test_validate_cyrillic_correct_value(self):
        self.assertTrue(self.test_instance.validate(u'my.москва.рф'))
        self.assertTrue(self.test_instance.validate(u'москва.рф'))
        self.assertTrue(self.test_instance.validate(u'ee.ёёё.ЕЁ'))

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate('a..b.s'))
        self.assertFalse(self.test_instance.validate('.a.b.s'))
        self.assertFalse(self.test_instance.validate('a.b.s..'))


class SrvNameTest(unittest.TestCase):
    def setUp(self):
        self.srv_record = types_network.SrvName()

    def test_validate(self):
        self.assertTrue(self.srv_record.validate("_sip._tcp.ra.ru"))
        self.assertTrue(self.srv_record.validate("_sip._tcp.tk"))
        self.assertTrue(self.srv_record.validate("_sip._tcp"))

        self.assertFalse(self.srv_record.validate("sip._tcp.ra.ru"))
        self.assertFalse(self.srv_record.validate("_sip.tcp.ra.ru"))
        self.assertFalse(self.srv_record.validate("hcb.jyg"))
