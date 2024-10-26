from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django import forms
from utils.django_service_objects.service_objects.services import ServiceWithResult  # noqa: E501


class RetrieveTokenService(ServiceWithResult):
    username = forms.CharField(max_length=50, required=True)
    password = forms.CharField(max_length=50, required=True)

    def process(self):
        self.result, _ = self._token
        return self

    @property
    def _token(self):
        return Token.objects.get_or_create(user=self._user)

    @property
    def _user(self):
        return authenticate(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password']
        )
