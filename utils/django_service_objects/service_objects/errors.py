class InvalidInputsError(Exception):
    """
    Raised during :class:`Service`'s :meth:`service_clean` method.
    Encapsulates both field_errors and non_field_errors into a single
    entity.

    :param dictionary errors: :class:`Services`'s ``errors`` dictionary

    :param dictionary non_field_errors: :class:`Service`'s
        ``non_field_errors`` dictionary
    """
    def __init__(self, errors, non_field_errors):
        self.errors = errors
        self.non_field_errors = non_field_errors

    def __repr__(self):
        return '{}({}, {})'.format(
            type(self).__name__, repr(self.errors), repr(self.non_field_errors))


import sys
import traceback


class Error(Exception):
    """
    Custom exception to handle response body correctly
    Attributes:
        translation_key (optional) -- unique key to use localization for message
        message (optional) -- message for users (will be used in case not found translation by translation_key)
        debug_message (optional) -- message for development team
        details (optional) -- error details, must contains object with next structure (example):
            details = {
                "field_or_key": [
                    {
                        "translation_key": string,
                        "message": string
                    }
                ]
            }
        additional_info (optional) -- non-structured object with valid JSON
                                      representation which contains some specific information
        response_status (optional) -- HTTP response status
        errors_dict (optional) -- dict which used for add errors in service objects

    """

    def __init__(
        self,
        translation_key=None,
        message=None,
        debug_message=None,
        details=None,
        additional_info=None,
        response_status=None,
        errors_dict=None,
    ) -> None:
        self.translation_key = translation_key or self._default_translation_key
        self.message = message or self._default_message
        self.debug_message = debug_message
        self.details = details
        self.additional_info = additional_info
        self.response_status = response_status or self._default_response_status
        self.errors_dict = errors_dict
        super().__init__(self.message)

    @property
    def _default_response_status(self):
        return 500

    @property
    def _default_message(self):
        return "We are sorry but something went wrong"

    @property
    def _default_translation_key(self):
        return "internal_server_error"


class Unauthorized(Error):
    @property
    def _default_response_status(self):
        return 401

    @property
    def _default_message(self):
        return "Authorization is required"

    @property
    def _default_translation_key(self):
        return "unauthorized"


class AuthenticationFailed(Error):
    @property
    def _default_response_status(self):
        return 401

    @property
    def _default_message(self):
        return "Authorization is required"

    @property
    def _default_translation_key(self):
        return "authentication_failed"


class AccessDenied(Error):
    @property
    def _default_response_status(self):
        return 423

    @property
    def _default_message(self):
        return "Access denied"

    @property
    def _default_translation_key(self):
        return "locked"


class NotFound(Error):
    @property
    def _default_response_status(self):
        return 404

    @property
    def _default_message(self):
        return "Resource not found"

    @property
    def _default_translation_key(self):
        return "not_found"


class ValidationError(Error):
    @property
    def _default_response_status(self):
        return 400

    @property
    def _default_message(self):
        return "Invalid request data"

    @property
    def _default_translation_key(self):
        return "invalid_request_data"


class ForbiddenError(Error):
    @property
    def _default_response_status(self):
        return 403

    @property
    def _default_message(self):
        return "Access denied"

    @property
    def _default_translation_key(self):
        return "forbidden"


class ServiceObjectLogicError(ValidationError):
    pass


def extend_exception_for_response(exception):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    translation_key = exception.translation_key if hasattr(exception,
                                                           "translation_key") else "internal_server_error"
    debug_message = exception.debug_message if hasattr(exception, "debug_message") else exc_value.__str__()
    details = exception.details if hasattr(exception, "details") else None
    additional_info = exception.additional_info if hasattr(exception, "additional_info") else None
    try:
        response_status = exception.response_status
    except AttributeError:
        response_status = 500
    try:
        message = exception.message
    except AttributeError:
        message = "We are sorry but something went wrong"

    error_dict = {
        "type": exc_type.__name__,
        "message": message,
        "translation_key": translation_key,
        "debug_message": debug_message,
        "backtrace": [line for index, line in
                      enumerate(traceback.format_exception(exc_type, exc_value, exc_traceback)) if index != 1],
        "details": details,
        "additional_info": additional_info
    }
    setattr(exception, 'response_dict', error_dict)
    setattr(exception, 'response_status', response_status)
    return exception