from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse


class StaticViewsTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_about_page_accessible_by_name(self):
        """URL, генерируемый при помощи имени
        about:author и about:tech, доступен."""
        templates_url = [reverse("about:author"), reverse("about:tech")]
        for adress in templates_url:
            with self.subTest(adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_about_page_uses_correct_template(self):
        """При запросе к about:..
        применяется шаблон about/..html."""
        templates = {
            reverse("about:author"): "about/author.html",
            reverse("about:tech"): "about/tech.html",
        }
        for adress, url in templates.items():
            with self.subTest(url=url):
                response = self.guest_client.get(adress)
                self.assertTemplateUsed(response, url)
                self.assertEqual(response.status_code, HTTPStatus.OK)
