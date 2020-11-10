from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from shared.decorators import handle_connection_error
from auth.models import Token
from auth.utils import json_response, token_required


@handle_connection_error
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)

        if username is not None and password is not None:
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    token = Token.objects.create(user=user)
                    allowed_nst_permissions = [perm.split("nst.")[1] for perm in user.get_all_permissions()
                                               if perm.startswith('nst')]
                    return json_response({
                        'token': token.token,
                        'username': user.username,
                        'user_permissions': allowed_nst_permissions
                    })
                else:
                    return json_response({
                        'error': 'Invalid User'
                    }, status=400)
            else:
                return json_response({
                    'error': 'Invalid Username/Password'
                }, status=400)
        else:
            return json_response({
                'error': 'Invalid Data'
            }, status=400)
    elif request.method == 'OPTIONS':
        return json_response({})
    else:
        return json_response({
            'error': 'Invalid Method'
        }, status=405)


@token_required
@handle_connection_error
def logout(request):
    if request.method == 'POST':
        request.token.delete()
        return json_response({
            'status': 'success'
        })
    elif request.method == 'OPTIONS':
        return json_response({})
    else:
        return json_response({
            'error': 'Invalid Method'
        }, status=405)
