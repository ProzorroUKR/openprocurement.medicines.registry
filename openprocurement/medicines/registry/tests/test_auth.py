# -*- coding: utf-8 -*-
from unittest import TestCase
from openprocurement.medicines.registry.auth import authenticated_role
from mock import MagicMock


class TestAuth(TestCase):
    def test_authenticated_role(self):
        request = MagicMock()
        self.assertEqual(authenticated_role(request), 'anonymous')
