from django.test import Client, TestCase
from django.urls import reverse


class ViewsTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_about_author_tech(self):
        """reverse("about:...") даёт /about/.../"""
        for name, url in (
            ("about:author", "/about/author/"),
            ("about:tech", "/about/tech/"),
        ):
            self.assertEqual(reverse(name), url)
