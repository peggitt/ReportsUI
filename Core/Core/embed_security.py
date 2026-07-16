import base64
import hashlib
import hmac
import logging
import time
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseForbidden, HttpResponseRedirect


logger = logging.getLogger("django.security.TrustedEmbed")


class TrustedEmbedMiddleware:
    """Allow portal pages only after a short-lived token from the Java system."""

    SESSION_KEY = "trusted_java_embed"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._is_exempt(request.path):
            return self.get_response(request)

        token = request.GET.get("embed_token")
        if token:
            if request.headers.get("Sec-Fetch-Dest") != "iframe":
                self._log_rejection(request, "token_not_in_iframe")
                return HttpResponseForbidden("This portal can only be opened inside the trusted system.")
            identity = self._verify(token)
            if identity is None:
                self._log_rejection(request, "invalid_or_expired_token")
                return HttpResponseForbidden("Invalid or expired portal access token.")
            request.session[self.SESSION_KEY] = identity
            logger.info(
                "Trusted portal token accepted path=%s user=%s origin=%s",
                request.path,
                identity["user_id"],
                request.headers.get("Referer", "-"),
            )
            query = request.GET.copy()
            query.pop("embed_token", None)
            location = request.path
            if query:
                location += "?" + urlencode(query, doseq=True)
            response = HttpResponseRedirect(location)
            return self._secure(response)

        if not request.session.get(self.SESSION_KEY):
            self._log_rejection(request, "missing_token_and_session")
            return HttpResponseForbidden("A portal access token is required.")

        # Prevent a URL copied from the iframe from being opened as a top-level page.
        if request.headers.get("Sec-Fetch-Dest") == "document":
            self._log_rejection(request, "top_level_navigation")
            return HttpResponseForbidden("This portal can only be opened inside the trusted system.")

        return self._secure(self.get_response(request))

    @staticmethod
    def _is_exempt(path):
        return path.startswith(("/static/", "/admin/"))

    @staticmethod
    def _log_rejection(request, reason):
        # Never log the token or full query string.
        logger.warning(
            "Trusted portal request rejected reason=%s path=%s token_present=%s "
            "session_present=%s destination=%s referer=%s",
            reason,
            request.path,
            bool(request.GET.get("embed_token")),
            bool(request.session.get(TrustedEmbedMiddleware.SESSION_KEY)),
            request.headers.get("Sec-Fetch-Dest", "-"),
            request.headers.get("Referer", "-"),
        )

    @staticmethod
    def _verify(token):
        secret = settings.REPORT_EMBED_SECRET.encode("utf-8")
        if not secret:
            return None
        try:
            payload_part, signature_part = token.split(".", 1)
            expected = hmac.new(secret, payload_part.encode("ascii"), hashlib.sha256).digest()
            supplied = base64.urlsafe_b64decode(signature_part + "=" * (-len(signature_part) % 4))
            if not hmac.compare_digest(expected, supplied):
                return None
            payload = base64.urlsafe_b64decode(payload_part + "=" * (-len(payload_part) % 4)).decode("utf-8")
            user_id, expires, nonce = payload.split(":", 2)
            if not user_id or not nonce or int(expires) < int(time.time()):
                return None
            return {"user_id": user_id, "expires": int(expires)}
        except (ValueError, TypeError, UnicodeError):
            return None

    @staticmethod
    def _secure(response):
        response["Content-Security-Policy"] = (
            "frame-ancestors " + " ".join(settings.REPORT_EMBED_ALLOWED_ANCESTORS)
        )
        # The response is user-specific and contains an authenticated iframe.
        response["Cache-Control"] = "no-store"
        return response
