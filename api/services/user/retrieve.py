from django.contrib.auth.models import User
from django import forms
from utils.django_service_objects.service_objects.services import ServiceWithResult  # noqa: E501
from utils.django_service_objects.service_objects.errors import NotFound


class RetrieveUserService(ServiceWithResult):
    id = forms.IntegerField()

    custom_validations = [
        'validate_presence_user',
    ]

    def process(self):
        self.run_custom_validations()
        if self.is_valid():
            self.result = self._profile
        return self

    @property
    def _user(self):
        return User.objects.get(id=self.cleaned_data['id'])

    def validate_presence_user(self):
        if not self._user:
            msg = f"Not found user with id = {self.cleaned_data['id']}"
            self.add_error(
                "id",
                NotFound(message=msg),
            )

