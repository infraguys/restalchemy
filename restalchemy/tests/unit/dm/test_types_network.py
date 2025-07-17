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

import netaddr
import unittest

from restalchemy.dm import types_network


class RecordNameTestCase(unittest.TestCase):

    def setUp(self):
        super(RecordNameTestCase, self).setUp()
        self.test_instance = types_network.RecordName()

    def test_validate_correct_value(self):
        self.assertTrue(self.test_instance.validate("ns1.ra.restalchemy.com"))
        self.assertTrue(self.test_instance.validate("ns1.55.restalchemy.com"))
        self.assertTrue(self.test_instance.validate("n_s1.55.restalchemy.com"))
        self.assertTrue(self.test_instance.validate("n-1.55.restalchemy.com"))
        self.assertTrue(self.test_instance.validate("restalchemy.com"))
        self.assertTrue(self.test_instance.validate("a.b.c.d.1.2.3"))
        self.assertTrue(self.test_instance.validate("qa-auto-dnsidxbs"))

    def test_from_simple_type(self):
        self.assertEqual(self.test_instance.from_simple_type(".x."), ".x")
        self.assertEqual(self.test_instance.from_simple_type(".x.x."), ".x.x")
        self.assertEqual(self.test_instance.from_simple_type("@"), "")

    def test_to_simple_type(self):
        self.assertEqual(self.test_instance.to_simple_type(""), "@")
        self.assertEqual(self.test_instance.to_simple_type("xxx"), "xxx")

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate("a..b.s"))
        self.assertFalse(self.test_instance.validate(".a.b.s"))
        self.assertFalse(self.test_instance.validate("a.b.s.."))
        self.assertFalse(self.test_instance.validate("my.москва.рф"))
        self.assertFalse(self.test_instance.validate("москва.рф"))
        self.assertFalse(self.test_instance.validate("ee.ёёё.ЕЁ"))


class RecordNameWithWildcardTestCase(unittest.TestCase):

    def setUp(self):
        super(RecordNameWithWildcardTestCase, self).setUp()
        self.test_instance = types_network.RecordNameWithWildcard()

    def test_validate_correct_value(self):
        self.assertTrue(
            self.test_instance.validate("*.ns1.ra.restalchemy.com")
        )
        self.assertTrue(self.test_instance.validate("ns1.ra.restalchemy.com"))
        self.assertTrue(self.test_instance.validate("*.restalchemy.com"))
        self.assertTrue(self.test_instance.validate("restalchemy.com"))

    def test_from_simple_type(self):
        self.assertEqual(self.test_instance.from_simple_type("*.x."), "*.x")
        self.assertEqual(
            self.test_instance.from_simple_type("*.x.x."), "*.x.x"
        )

    def test_to_simple_type(self):
        self.assertEqual(self.test_instance.to_simple_type("*.xxx"), "*.xxx")

    def test_validate_incorrect_value(self):
        self.assertFalse(self.test_instance.validate("*.a..b.s"))
        self.assertFalse(self.test_instance.validate("a.*.b.s"))
        self.assertFalse(self.test_instance.validate(".a.b.s"))
        self.assertFalse(self.test_instance.validate("*a.b.s"))
        self.assertFalse(self.test_instance.validate("a.b.s*"))
        self.assertFalse(self.test_instance.validate("a.b*.s"))
        self.assertFalse(self.test_instance.validate("a.b.s..*"))


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


class HostnameTest(unittest.TestCase):
    def setUp(self):
        super(HostnameTest, self).setUp()
        self.fqdn = types_network.Hostname()
        self.fqdn_2level = types_network.Hostname(min_levels=2)
        self.fqdn_with_leading_underscore = types_network.Hostname(
            allow_leading_underscore=True
        )
        self.fqdn_with_middle_underscore = types_network.Hostname(
            allow_middle_underscore=True
        )

    def test_validate(self):
        data = [
            "first-level",
            "test-me.me",
            "fe.fe",
            "aa",
            "a.bc",
            "1.2.3.4.com",
            "xn--kxae4bafwg.xn--pxaix.gr",
            "a23456789-123456789-123456789-123456789-123456789-123456789-123."
            "b23.com",
            "a23456789-a23456789-a234567890.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a234567.com",
            "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcde."
            "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk."
            "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk."
            "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk."
            "com",
        ]
        for fqdn in data:
            self.assertTrue(self.fqdn.validate(fqdn), fqdn)

    def test_validate_underscore(self):
        data = ["_acme-challenge.example.com", "_acme-challenge"]

        for fqdn in data:
            self.assertTrue(
                self.fqdn_with_leading_underscore.validate(fqdn), fqdn
            )

    def test_validate_underscore_negative(self):
        data = ["_acme-challenge._example.com"]

        for fqdn in data:
            self.assertFalse(
                self.fqdn_with_leading_underscore.validate(fqdn), fqdn
            )

    def test_validate_middle_underscore(self):
        data = ["abc_def.example.com"]

        for fqdn in data:
            self.assertTrue(
                self.fqdn_with_middle_underscore.validate(fqdn), fqdn
            )

    def test_validate_middle_underscore_negative(self):
        data = [
            "www_.example.com",
            "_www.example.com",
            "www.example._com",
            "www.example.com_",
            "www.example.co_m",
            "news.ae_ro",
        ]

        for fqdn in data:
            self.assertFalse(
                self.fqdn_with_middle_underscore.validate(fqdn), fqdn
            )

    def test_validate_negative(self):
        data = [
            "тест.ру",
            "-fe.fe",
            "fe-.fe",
            "_fe.fe",
            "f_e.fe",
            "fe_.fe",
            "a..bc",
            "ec2-35-160-210-253.us-west-2-.compute.amazonaws.com",
            "-ec2_35$160%210-253.us-west-2-.compute.amazonaws.com",
            "ec2-35-160-210-253.us-west-2-.compute.amazonaws.com",
            "a23456789-123456789-123456789-123456789-123456789-123456789-1234."
            "b23.com",
            "a23456789-a23456789-a234567890.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.com",
            "mx.gmail.com.",
            "a23456789-a23456789-a234567890.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.com",
        ]
        for fqdn in data:
            self.assertFalse(self.fqdn.validate(fqdn), fqdn)

    def test_min_levels(self):
        data = [
            "test-me.me",
            "fe.fe",
            "a.bc",
            "1.2.3.4.com",
        ]
        for fqdn in data:
            self.assertTrue(self.fqdn_2level.validate(fqdn), fqdn)

    def test_min_levels_negative(self):
        data = [
            "first-level",
            "aa",
        ]
        for fqdn in data:
            self.assertFalse(self.fqdn_2level.validate(fqdn), fqdn)


class FQDNTest(unittest.TestCase):
    def setUp(self):
        super(FQDNTest, self).setUp()
        self.fqdn = types_network.FQDN()
        self.fqdn_2level = types_network.FQDN(min_levels=2)

    def test_validate(self):
        data = [
            "first_level.",
            "test_me.me.",
            "fe.fe.",
            "aa.",
            "a.bc.",
            "1.2.3.4.com.",
            "xn--kxae4bafwg.xn--pxaix.gr.",
            "a23456789-123456789-123456789-123456789-123456789-123456789-123."
            "b23.com.",
            "a23456789-a23456789-a234567890.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a234567.com.",
            "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcde."
            "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk."
            "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk."
            "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk."
            "com.",
        ]
        for fqdn in data:
            self.assertTrue(self.fqdn.validate(fqdn), fqdn)

    def test_validate_negative(self):
        data = [
            "тест.ру.",
            "-fe.fe.",
            "a..bc.",
            "ec2-35-160-210-253.us-west-2-.compute.amazonaws.com.",
            "-ec2_35$160%210-253.us-west-2-.compute.amazonaws.com.",
            "ec2-35-160-210-253.us-west-2-.compute.amazonaws.com.",
            "a23456789-123456789-123456789-123456789-123456789-123456789-1234."
            "b23.com.",
            "a23456789-a23456789-a234567890.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.com.",
            "mx.gmail.com",
            "a23456789-a23456789-a234567890.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.a23456789.a23456789.a23456789.a23456789.a23456789."
            "a23456789.com.",
        ]
        for fqdn in data:
            self.assertFalse(self.fqdn.validate(fqdn), fqdn)

    def test_min_levels(self):
        data = [
            "test_me.me.",
            "fe.fe.",
            "a.bc.",
            "1.2.3.4.com.",
        ]
        for fqdn in data:
            self.assertTrue(self.fqdn_2level.validate(fqdn), fqdn)

    def test_min_levels_negative(self):
        data = [
            "first_level.",
            "aa.",
        ]
        for fqdn in data:
            self.assertFalse(self.fqdn_2level.validate(fqdn), fqdn)


class IPRangeTest(unittest.TestCase):
    def setUp(self):
        self.ip_range = types_network.IPRange()

    def test_validate(self):
        correct_range = netaddr.IPRange("10.0.0.0", "10.0.1.0")
        self.assertTrue(self.ip_range.validate(correct_range))

        incorrect_range = "10.0.0.0-10.0.1.0"
        self.assertFalse(self.ip_range.validate(incorrect_range))

    def test_to_simple_type(self):
        foo_range = netaddr.IPRange("10.0.0.0", "10.0.1.0")
        self.assertEqual(
            self.ip_range.to_simple_type(foo_range), "10.0.0.0-10.0.1.0"
        )

    def test_from_simple_type(self):
        foo_range = netaddr.IPRange("10.0.0.0", "10.0.1.0")
        self.assertEqual(
            self.ip_range.from_simple_type("10.0.0.0-10.0.1.0"), foo_range
        )

    def test_from_unicode(self):
        foo_range = netaddr.IPRange("10.0.0.0", "10.0.1.0")
        self.assertEqual(
            self.ip_range.from_unicode("10.0.0.0-10.0.1.0"), foo_range
        )
