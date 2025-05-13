# accounts/middleware.py
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
# from django.contrib.auth import get_user_model # <<< KHÔNG DÙNG get_user_model nữa
from .models import CustomUser # <<< IMPORT TRỰC TIẾP CustomUser
from urllib.parse import parse_qs
import traceback 

# User = get_user_model() # <<< Bỏ dòng này

@database_sync_to_async
def get_user_from_token(token_key):
    """
    Attempts to authenticate a user using a JWT token.
    QUAN TRỌNG: Sử dụng trực tiếp CustomUser model.
    """
    if not token_key:
        print("WebSocket Auth (get_user_from_token): No token key provided.")
        return AnonymousUser()
    try:
        token = AccessToken(token_key)
        payload = token.payload 
        print(f"WebSocket Auth (get_user_from_token): Token Payload: {payload}")

        # Vẫn lấy user ID dựa trên cấu hình SIMPLE_JWT['USER_ID_CLAIM']
        # Trong settings.py của bạn là 'admin_user_id'
        user_id_claim_name = 'admin_user_id' 
        user_id_from_payload = payload.get(user_id_claim_name)

        if user_id_from_payload is None:
            # Thử lại với 'user_id' mặc định nếu claim chính không có
            user_id_from_payload = payload.get('user_id') 
            if user_id_from_payload is None:
                print(f"WebSocket Auth (get_user_from_token): Neither '{user_id_claim_name}' nor 'user_id' found.")
                return AnonymousUser()
        
        print(f"WebSocket Auth (get_user_from_token): Attempting to fetch CustomUser with ID: {user_id_from_payload}")
        # --- SỬA Ở ĐÂY: Dùng trực tiếp CustomUser ---
        user = CustomUser.objects.get(id=user_id_from_payload) 
        print(f"WebSocket Auth (get_user_from_token): CustomUser {user.email} authenticated.")
        return user
        # -------------------------------------------
    # ... (Các khối except giữ nguyên, nhưng thay User.DoesNotExist nếu có) ...
    except CustomUser.DoesNotExist: # <<< Sửa except nếu bạn có dùng User.DoesNotExist
        actual_id_used = user_id_from_payload if 'user_id_from_payload' in locals() and user_id_from_payload is not None else "ID_NOT_EXTRACTED"
        print(f"WebSocket Auth (get_user_from_token): CustomUser with ID {actual_id_used} does not exist.")
        return AnonymousUser()
    except InvalidToken: # Các except khác giữ nguyên
        print(f"WebSocket Auth (get_user_from_token): Invalid token (InvalidToken exception): {token_key[:20]}...")
        traceback.print_exc()
        return AnonymousUser()
    except TokenError as e:
        print(f"WebSocket Auth (get_user_from_token): Token error (TokenError exception): {e} for token: {token_key[:20]}...")
        traceback.print_exc()
        return AnonymousUser()
    except Exception as e:
        print(f"WebSocket Auth (get_user_from_token): An unexpected error occurred: {e}")
        traceback.print_exc()
        return AnonymousUser()

class TokenAuthMiddleware:
    # ... (Phần __init__ và __call__ giữ nguyên như trước) ...
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope_copy = dict(scope) 
        query_string = scope_copy.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        # print(f"TokenAuthMiddleware: Incoming query string: {query_string}") # Bỏ bớt log
        if token:
            # print(f"TokenAuthMiddleware: Token found: {token[:20]}...")
            # Gọi hàm get_user_from_token đã sửa để dùng CustomUser trực tiếp
            scope_copy['user'] = await get_user_from_token(token) 
        else:
            # print("TokenAuthMiddleware: No 'token' in query string.")
            if 'user' not in scope_copy:
                 scope_copy['user'] = AnonymousUser()
        
        final_user_in_scope = scope_copy.get('user', AnonymousUser())
        user_email_log = getattr(final_user_in_scope, 'email', 'Anonymous')
        # print(f"TokenAuthMiddleware: Passing user to next layer: {user_email_log} (Type: {type(final_user_in_scope)})")
        
        return await self.app(scope_copy, receive, send)