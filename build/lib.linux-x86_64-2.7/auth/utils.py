import json
from django.http import HttpResponse
from auth.models import Token
from datetime import datetime
from shared.decorators import handle_connection_error


def json_response(response_dict, status=200):
    response = HttpResponse(json.dumps(response_dict), content_type="application/json", status=status)
    return response

@handle_connection_error
def token_required(func):

    def inner(request, *args, **kwargs):
        if request.method == 'OPTIONS':
            return func(request, *args, **kwargs)

        auth_header = request.META.get('HTTP_AUTHORIZATION', None)
        if auth_header is not None:
            tokens = auth_header.split(' ')
            if len(tokens) == 2 and tokens[0] == 'Token':
                token = tokens[1]
                try:
                    stored_token = Token.objects.get(token=token)
                    if datetime.now() > stored_token.expires:
                        stored_token.delete()
                        return json_response({
                            'error': True,
                            'error_message': 'Session Expired'
                        }, status=401)
                    request.token = stored_token
                    request.user = request.token.user
                    return func(request, *args, **kwargs)
                except Token.DoesNotExist:
                    return json_response({
                        'error': True,
                        'error_message': 'Unkown session'
                    }, status=401)
        return json_response({
            'error': True,
            'error_message': "Header doesn't contain authentication token"
        }, status=401)

    return inner