#!/usr/bin/env python
# -*- coding: utf-8 -*-

__authors__ = 'Bruno Adelé <bruno@adele.im>'
__copyright__ = 'Copyright (C) 2013 Bruno Adelé'
__description__ = """Unittest"""
__license__ = 'GPLv3'


import os
import unittest

from SDRHunter import SDRHunter


class TestPackages(unittest.TestCase):

    def test_template(self):
        self.assertTrue(True)

    def test_version(self):
        with self.assertRaises(SystemExit) as cm:
            cmd = "-v"
            args = SDRHunter.parse_arguments(cmd.split())
        self.assertEqual(cm.exception.code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
