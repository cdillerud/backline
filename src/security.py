"""Single shared-password gate for a private preview. Not a multiuser authorization system."""
import hmac
import os
from fastapi import Request
from fastapi.responses import JSONResponse


def install_preview_auth(app):
    @app.middleware('http')
    async def preview_auth(request: Request, call_next):
        if request.url.path == '/api/health':
            return await call_next(request)
        username = os.getenv('BACKLINE_PREVIEW_USER', '')
        password = os.getenv('BACKLINE_PREVIEW_PASSWORD', '')
        # Fail closed when publicly hosted; explicitly opt out only for local development.
        if not username or not password:
            if os.getenv('BACKLINE_LOCAL_DEV') == '1':
                return await call_next(request)
            return JSONResponse({'detail': 'Preview credentials not configured'}, status_code=503)
        from base64 import b64decode
        from binascii import Error
        header = request.headers.get('authorization', '')
        try:
            scheme, token = header.split(' ', 1)
            decoded = b64decode(token, validate=True).decode('utf-8')
            provided_user, provided_password = decoded.split(':', 1)
            valid = scheme.lower() == 'basic' and hmac.compare_digest(provided_user, username) and hmac.compare_digest(provided_password, password)
        except (ValueError, UnicodeDecodeError, Error):
            valid = False
        if not valid:
            return JSONResponse({'detail': 'Authentication required'}, status_code=401, headers={'WWW-Authenticate': 'Basic realm="Backline Private Preview"', 'Cache-Control': 'no-store'})
        return await call_next(request)
