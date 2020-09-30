# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# Make coding more python3-ish
from __future__ import absolute_import, division, print_function

__metaclass__ = type


from ansible_collections.ansible.netcommon.tests.unit.compat import unittest
from ansible_collections.ansible.netcommon.plugins.module_utils.network.common.index_of import (
    index_of,
)


class TestIndexOfFilter(unittest.TestCase):
    def test_fail_no_qualfier(self):
        obj, test, value, _answer = [1, 2], "@@", 1, 0
        with self.assertRaises(Exception) as exc:
            index_of(obj, test, value)
        self.assertIn("no test named '@@'", str(exc.exception))
        obj, test, value, key, _answer = [{"a": 1}], "@@", 1, "a", 0
        with self.assertRaises(Exception) as exc:
            index_of(obj, test, value, key)
        self.assertIn("no test named '@@'", str(exc.exception))

    def test_fail_not_a_list(self):
        obj, test, value = True, "==", 1
        with self.assertRaises(Exception) as exc:
            index_of(obj, test, value)
        self.assertIn(
            "a list is required, was passed a 'bool'", str(exc.exception)
        )

    def test_fail_wantlist_not_a_bool(self):
        obj, test, value, _answer = [1, 2], "==", 1, 0
        with self.assertRaises(Exception) as exc:
            index_of(obj, test, value, wantlist=42)
        self.assertIn(
            "'wantlist' is required to be a bool, was passed a 'int'",
            str(exc.exception),
        )

    # def test_fail_too_many_args(self):
    #     obj, test, value, _answer = [1, 2], "==", 1, 0
    #     with self.assertRaises(Exception) as exc:
    #         index_of(obj, test, value, 42, 42, 42)
    #     self.assertIn("only 1-3 parameters", str(exc.exception))

    def test_fail_mixed_list(self):
        obj, test, value, key = [{"a": "b"}, True, 1, "a"], "==", "b", "a"
        with self.assertRaises(Exception) as exc:
            index_of(obj, test, value, key)
        self.assertIn("required to be dictionaries", str(exc.exception))

    def test_fail_key_not_valid(self):
        obj, test, value, key = [{"a": "b"}], "==", "b", [1, 2]
        with self.assertRaises(Exception) as exc:
            index_of(obj, test, value, key)
        self.assertIn("Unknown key type", str(exc.exception))

    def test_fail_on_missing(self):
        obj, test, value, key = [{"a": True}, {"c": False}], "==", True, "a"
        with self.assertRaises(Exception) as exc:
            index_of(obj, test, value, key, fail_on_missing=True)
        self.assertIn("'a' was not found", str(exc.exception))

    def test_just_test(self):
        objs = [
            ([True], "true", 0),
            ([False, 5], "boolean", 0),
            ([0, False], "false", 1),
            ([3, 4], "even", 1),
            ([3, 3], "even", []),
            ([3, 3, 3, 4], "odd", [0, 1, 2]),
            ([3.3, 3.4], "float", [0, 1]),
        ]
        for entry in objs:
            obj, test, answer = entry
            result = index_of(obj, test)
            expected = answer
            self.assertEqual(result, expected)

    def test_simple_lists(self):
        objs = [
            ([1, 2, 3], "==", 2, 1),
            (["a", "b", "c"], "eq", "c", 2),
            ([True, False, 0, 1], "equalto", False, [1, 2]),
            ([True, False, "0", "1"], "==", False, 1),
            ([True, False, "", "1"], "==", False, 1),
            ([True, False, "", "1"], "in", False, 1),
            ([True, False, "", "1", "a"], "in", [False, "1"], [1, 3]),
            ([1, 2, 3, "a", "b", "c"], "!=", "c", [0, 1, 2, 3, 4]),
            ([1, 2, 3], "!<", 3, 2),
        ]
        for entry in objs:
            obj, test, value, answer = entry
            result = index_of(obj, test, value)
            expected = answer
            self.assertEqual(result, expected)

    def test_simple_dict(self):
        objs = [
            ([{"a": 1}], "==", 1, "a", 0),
            ([{"a": 1}], "==", 1, "b", []),
            ([{"a": 1}], "==", 2, "a", []),
            (
                [{"a": 1}, {"a": 1}, {"a": 1}, {"a": 2}],
                "==",
                1,
                "a",
                [0, 1, 2],
            ),
            (
                [{"a": "abc"}, {"a": "def"}, {"a": "ghi"}, {"a": "jkl"}],
                "match",
                "^a",
                "a",
                0,
            ),
            (
                [{"a": "abc"}, {"a": "def"}, {"a": "ghi"}, {"a": "jkl"}],
                "search",
                "e",
                "a",
                1,
            ),
        ]
        for entry in objs:
            obj, test, value, key, answer = entry
            result = index_of(obj, test, value, key)
            self.assertEqual(result, answer)