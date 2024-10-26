import abc
from contextlib import contextmanager

from django import forms
from django.db import transaction, DEFAULT_DB_ALIAS
from django.forms.forms import DeclarativeFieldsMetaclass
from django.forms.models import ModelFormMetaclass
import six

from .errors import InvalidInputsError, ServiceObjectLogicError


class ServiceMetaclass(abc.ABCMeta, DeclarativeFieldsMetaclass):
    pass


@six.add_metaclass(ServiceMetaclass)
class Service(forms.Form):
    """
    Based on Django's :class:`Form`, designed to encapsulate
    Business Rules functionality.  Input values are validated against
    the Service's defined fields before calling main functionality::

        class UpdateUserEmail(Service):
            user = ModelField(User)
            new_email = forms.EmailField()

            def process(self):
                old_email = user.email
                user.email = self.cleaned_data['new_email']
                user.save()

                send_email(
                    'Email Update',
                    'Your email was changed',
                    'system',
                    [old_email]
                )


        user = User.objects.get(id=20)

        UpdateUserEmail.execute({
            'user': user,
            'new_email': 'John.Smith@example.com'
        })


    :cvar boolean db_transaction: controls if :py:meth:`execute`
        is performed inside a Django database transaction.  Default
        is True.

    :cvar string using: In a multiple database setup, controls which
        database connection is used from the transaction.  Defaults
        to DEFAULT_DB_ALIAS which works in a single database setup.

    """

    db_transaction = True
    run_post_process = True
    using = DEFAULT_DB_ALIAS

    @classmethod
    def execute(cls, inputs, files=None, **kwargs):
        """
        Function to be called from the outside to kick off the Service
        functionality.

        :param dictionary inputs: data parameters for Service, checked
            against the fields defined on the Service class.

        :param dictionary files: usually request's FILES dictionary or
            None.

        :param dictionary **kwargs: any additional parameters Service may
            need, can be an empty dictionary
        """
        instance = cls(inputs, files, **kwargs)
        instance.service_clean()
        with instance._process_context():
            return instance.process()

    def service_clean(self):
        """
        Calls base Form's :meth:`is_valid` to verify ``inputs`` against
        Service's fields and raises :class:`InvalidInputsError` if necessary.
        """
        if not self.is_valid():
            raise InvalidInputsError(self.errors, self.non_field_errors())

    @abc.abstractmethod
    def process(self):
        """
        Main method to be overridden; contains the Business Rules
        functionality.
        """
        pass

    @contextmanager
    def _process_context(self):
        """
        Returns the context for :meth:`process`
        :return:
        """
        if self.db_transaction:
            with transaction.atomic(using=self.using):
                if self.run_post_process:
                    transaction.on_commit(self.post_process)
                yield
        else:
            yield
            if self.run_post_process:
                self.post_process()

    def post_process(self):
        """
        Post process method to be perform extra actions once :meth:`process`
        successfully executes.
        """
        pass


class ModelServiceMetaclass(ServiceMetaclass, ModelFormMetaclass):
    pass


class ModelService(six.with_metaclass(ModelServiceMetaclass, Service)):
    """
    Same as :class:`Service` but auto-creates fields based on the provided
    :class:`Model`.  Additionally, You can manually create fields to override
    or extend the auto-created fields::

        class Person(models.Model):
            first_name = models.CharField(max_length=30)
            last_name = models.CharField(max_length=30)
            email = models.EmailField()


        class CreatePersonService(Service):
            class Meta:
                model = Person
                fields = '_all_'

            notify = forms.BooleanField()

            def process(self):
                person = Person(
                    first_name = self.cleaned_data['first_name'],
                    last_name = self.cleaned_data['last_name'],
                    email = self.cleaned_data['email']
                )
                person.save()

                if self.cleaned_data['notify']:
                    django.send_mail(
                        'Account Created',
                        'An account has been created for you'
                        'System',
                        [person.email]
                    )


        CreatePersonService.execute({
            'first_name': 'John',
            'last_name': 'Smith',
            'notify': True
        })
    """
    pass


class ServiceWithResult(Service, abc.ABC):
    """
    Add result field into Service object
    """

    custom_validations = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result = None
        self.response_status = None

    def run_custom_validations(self):
        for custom_validation in self.__class__.custom_validations:
            getattr(self, custom_validation)()

    # Modified clean method to handle Django form errors in our way
    def service_clean(self):
        if not self.is_valid():
            try:
                errors = self.errors.as_data()
            except AttributeError:
                errors = self.errors
            raise InvalidInputsError(errors, self.non_field_errors())

    # Modified add_error method to handle Django form errors with no fields keys in our way
    def add_error(self, field, error, field_index=None):
        if field_index is None:
            prepared_error = getattr(error, 'errors', None) or getattr(error, 'errors_dict', None) or error
            if self._errors.get(field):
                self._errors[field].append(prepared_error)
            else:
                self._errors[field] = [prepared_error]
        else:
            prepared_error = getattr(error, 'errors', None) or getattr(error, 'errors_dict', None) or error
            if self._errors.get(field):
                if self._errors[field].get(field_index):
                    self._errors[field][field_index].append(prepared_error)
                else:
                    self._errors[field][field_index] = [prepared_error]
            else:
                self._errors[field] = { field_index: [prepared_error] }

    def stop_process(self):
        if bool(self._errors):
            raise ServiceObjectLogicError(errors_dict=self._errors, response_status=self.response_status or 400)
        else:
            return self


class ServiceOutcome:
    """
    Wrapper to execute Service objects
    """

    def __init__(self, service_object, service_object_attributes=None, service_object_files=None):
        self._errors = {}
        self._result = None
        self._response_status = None
        self._outcome = self.execute(service_object, service_object_attributes, service_object_files)

    def execute(self, service_object, service_object_attributes, service_object_files):
        outcome = service_object.execute(service_object_attributes, service_object_files)
        self._response_status = outcome.response_status
        if bool(outcome.errors):
            response_status = self.response_status if hasattr(self, "response_status") else 400
            raise ServiceObjectLogicError(errors_dict=outcome.errors, response_status=response_status)
        else:
            self._result = outcome.result
        return outcome

    @property
    def valid(self):
        return not bool(self._errors)

    @property
    def service(self):
        return self._outcome

    @property
    def result(self):
        return self._result

    @property
    def errors(self):
        return self._errors

    @property
    def response_status(self):
        return self._response_status
