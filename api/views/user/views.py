from rest_framework.views import APIView
from rest_framework.response import Response
from api.serializers.user.serializers import UserSerializer
from api.services.user.retrieve import RetrieveUserService
from rest_framework.permissions import IsAuthenticated
from utils.django_service_objects.service_objects.services import ServiceOutcome  # noqa: E501
from rest_framework import status
from api.services.token.retrieve import RetrieveTokenService
from api.services.user.create import CreateUserService


class UserView(APIView):
    permission_classes = [IsAuthenticated,]
    def get(self, request):
        outcome = ServiceOutcome(RetrieveUserService, {'id': request.user.id})
        return Response(UserSerializer(outcome.result).data, status=status.HTTP_200_OK)


class RegisterView(APIView):
    def post(self, request):
        ServiceOutcome(CreateUserService, request.data)
        outcome = ServiceOutcome(RetrieveTokenService, request.data)
        return Response(
            {'auth_token': str(outcome.result)},
            status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    def post(self, request):
        outcome = ServiceOutcome(RetrieveTokenService, request.data)
        return Response(
            {'auth_token': str(outcome.result)},
            status=status.HTTP_200_OK
        )
