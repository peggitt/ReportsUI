import base64
import hashlib
import hmac
import time

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from Core.embed_security import TrustedEmbedMiddleware


@override_settings(
    REPORT_EMBED_SECRET="test-secret",
    REPORT_EMBED_ALLOWED_ANCESTORS=["https://core.example.test"],
)
class TrustedEmbedMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = TrustedEmbedMiddleware(lambda request: HttpResponse("ok"))

    def request(self, path, destination=None):
        headers = {"HTTP_SEC_FETCH_DEST": destination} if destination else {}
        request = self.factory.get(path, **headers)
        SessionMiddleware(lambda value: value).process_request(request)
        return request

    @staticmethod
    def token(expires=None):
        payload = "operator1:%s:nonce" % (expires or int(time.time()) + 60)
        payload_part = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
        signature = hmac.new(b"test-secret", payload_part.encode(), hashlib.sha256).digest()
        signature_part = base64.urlsafe_b64encode(signature).decode().rstrip("=")
        return payload_part + "." + signature_part

    def test_valid_iframe_token_starts_session_and_redirects_without_token(self):
        request = self.request("/?embed_token=" + self.token(), "iframe")
        response = self.middleware(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")
        self.assertEqual(request.session["trusted_java_embed"]["user_id"], "operator1")
        self.assertEqual(
            response["Content-Security-Policy"],
            "frame-ancestors https://core.example.test",
        )
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_token_is_rejected_for_top_level_navigation(self):
        response = self.middleware(self.request("/?embed_token=" + self.token(), "document"))
        self.assertEqual(response.status_code, 403)

    def test_expired_token_is_rejected(self):
        response = self.middleware(self.request("/?embed_token=" + self.token(1), "iframe"))
        self.assertEqual(response.status_code, 403)

    def test_request_without_embed_session_is_rejected(self):
        response = self.middleware(self.request("/reports/", "iframe"))
        self.assertEqual(response.status_code, 403)
