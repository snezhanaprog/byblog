import pickle
import datetime

import six
from django import forms
from django.test import TestCase

from service_objects.errors import InvalidInputsError
from service_objects.services import ModelService
from tests.models import CustomFooModel, FooModel
from tests.services import (FooService, MockService, NoDbTransactionService,
                            FooModelService)

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch


MockService.process = Mock()
MockService.post_process = Mock()
NoDbTransactionService.process = Mock()
NoDbTransactionService.post_process = Mock()

class ServiceTest(TestCase):

    def test_base_class(self):
        MockService.execute({'bar': 'Hello'})

        MockService.process.assert_called_with()

    def test_process_implemented(self):
        with self.assertRaises(TypeError):
            FooService.execute({'bar': 'Hello'})

    def test_fields(self):
        with self.assertRaises(InvalidInputsError):
            MockService.execute({})

        MockService.execute({'bar': 'Hello'})

    def test_invalid_inputs_error(self):
        with self.assertRaises(InvalidInputsError) as cm:
            MockService.execute({})

        self.assertIn('InvalidInputsError', repr(cm.exception))
        self.assertIn('bar', repr(cm.exception))
        self.assertIn('This field is required.', repr(cm.exception))

    @patch('service_objects.services.transaction')
    def test_db_transaction_flag(self, mock_transaction):

        NoDbTransactionService.execute({})
        assert not mock_transaction.atomic.return_value.__enter__.called

        MockService.execute({'bar': 'Hello'})
        assert mock_transaction.atomic.return_value.__enter__.called

    @patch('service_objects.services.transaction')
    def test_has_post_process_action_flag(self, mock_transaction):
        NoDbTransactionService.execute({})
        assert not mock_transaction.atomic.return_value.__enter__.called
        NoDbTransactionService.process.assert_called_with()

        MockService.execute({'bar': 'Hello'})
        assert mock_transaction.atomic.return_value.__enter__.called
        assert mock_transaction.on_commit.called_once_with(MockService.post_process)


class ModelServiceTest(TestCase):

    def test_auto_fields(self):

        class FooModelService(ModelService):
            class Meta:
                model = FooModel
                fields = '__all__'

            def process(self):
                pass

        f = FooModelService()

        field_names = list(six.iterkeys(f.fields))
        self.assertEqual(1, len(field_names))
        self.assertEqual('one', field_names[0])

    def test_extra_fields(self):

        class FooModelService(ModelService):
            two = forms.CharField()

            class Meta:
                model = FooModel
                fields = '__all__'

            def process(self):
                pass

        f = FooModelService()

        field_names = list(six.iterkeys(f.fields))
        self.assertEqual(2, len(field_names))
        self.assertEqual('one', field_names[0])
        self.assertEqual('two', field_names[1])
