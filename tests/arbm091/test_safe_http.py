import unittest
from arbm_safe_http import validate_url


class SafeHTTPContractTests(unittest.TestCase):
    def test_https_public_host_is_allowed(self):
        scheme,host,port,path=validate_url(
            "https://api.groq.com/openai/v1/chat/completions",
            allowed_hosts=("api.groq.com",))
        self.assertEqual((scheme,host,port),("https","api.groq.com",443))
        self.assertEqual(path,"/openai/v1/chat/completions")

    def test_plain_http_public_host_is_forbidden(self):
        with self.assertRaisesRegex(ValueError,"SAFE_HTTP_PLAINTEXT_FORBIDDEN"):
            validate_url("http://example.com/api")

    def test_loopback_http_requires_explicit_opt_in(self):
        with self.assertRaisesRegex(ValueError,"SAFE_HTTP_PLAINTEXT_FORBIDDEN"):
            validate_url("http://127.0.0.1:8000/api")
        self.assertEqual(
            validate_url("http://127.0.0.1:8000/api",allow_loopback_http=True)[1],
            "127.0.0.1")

    def test_private_http_requires_explicit_infrastructure_opt_in(self):
        with self.assertRaisesRegex(ValueError,"SAFE_HTTP_PLAINTEXT_FORBIDDEN"):
            validate_url("http://172.18.0.2:5000/api")
        self.assertEqual(
            validate_url("http://172.18.0.2:5000/api",allow_private_http=True)[1],
            "172.18.0.2")

    def test_private_https_literal_is_forbidden(self):
        with self.assertRaisesRegex(ValueError,"SAFE_HTTP_PRIVATE_IP_FORBIDDEN"):
            validate_url("https://10.0.0.1/api")

    def test_userinfo_fragment_and_wrong_host_are_forbidden(self):
        with self.assertRaisesRegex(ValueError,"SAFE_HTTP_AUTHORITY_INVALID"):
            validate_url("https://user:pass@example.com/api")
        with self.assertRaisesRegex(ValueError,"SAFE_HTTP_FRAGMENT_FORBIDDEN"):
            validate_url("https://example.com/api#secret")
        with self.assertRaisesRegex(ValueError,"SAFE_HTTP_HOST_NOT_ALLOWLISTED"):
            validate_url("https://evil.example/api",allowed_hosts=("api.groq.com",))


if __name__=="__main__":
    unittest.main()
