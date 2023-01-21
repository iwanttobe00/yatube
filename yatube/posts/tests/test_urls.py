from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse


from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="auth")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание",
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text="Тестовая пост",
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.user = self.post.author
        self.authorized_client = Client()
        self.authorized_client.force_login(PostURLTests.user)

    def test_urls(self):
        """Всем главная страница доступна"""
        response = self.guest_client.get(reverse("posts:index"))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_posts_edit(self):
        """Только автор может редачить"""
        response = self.authorized_client.get(reverse("posts:post_create"))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create(self):
        """Чел который залогинин"""
        response = self.guest_client.get(reverse("posts:post_create"))
        self.assertRedirects(response, "/auth/login/?next=/create/")

    def test_unexisting_page(self):
        """Ошыыбка"""
        response = self.guest_client.get("/unexisting_page/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            reverse("posts:index"): "posts/index.html",
            reverse("posts:post_create"): "posts/create_post.html",
            reverse("posts:group_list", kwargs={"slug": self.group.slug}):
                "posts/group_list.html",
            reverse("posts:post_detail", kwargs={"post_id": self.post.id}):
                "posts/post_detail.html",
            reverse("posts:profile", kwargs={"username": self.user.username}):
                "posts/profile.html",
            reverse("posts:post_edit", kwargs={"post_id": self.post.id}):
                "posts/create_post.html",
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
