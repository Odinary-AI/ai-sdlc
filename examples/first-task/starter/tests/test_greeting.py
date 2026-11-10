import unittest

from greeting import greeting


class GreetingTests(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(greeting("Ada"), "Hello, Ada!")

    def test_trim(self):
        self.assertEqual(greeting("  Ada\t"), "Hello, Ada!")

    def test_empty(self):
        for name in ("", " \t"):
            with self.subTest(name=name):
                self.assertEqual(greeting(name), "Hello, stranger!")

    def test_unicode_and_internal_space(self):
        self.assertEqual(greeting("小 明"), "Hello, 小 明!")
