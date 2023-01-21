import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Follow, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="auth")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Что-то о группе",
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text="Текст поста",
            group=cls.group,
        )
        cls.templates_pages_names = {
            reverse("posts:index"):
            "posts/index.html",
            reverse("posts:group_list", kwargs={"slug": cls.group.slug}):
            "posts/group_list.html",
            reverse("posts:profile", kwargs={"username": cls.post.author}):
            "posts/profile.html",
            reverse("posts:post_detail", kwargs={"post_id": cls.post.id}):
            "posts/post_detail.html",
            reverse("posts:post_edit", kwargs={"post_id": cls.post.id}):
            "posts/create_post.html",
            reverse("posts:post_create"): "posts/create_post.html",
        }
        cls.comment = Comment.objects.create(
            author=cls.user,
            text="Текстовый комментарий"
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostViewsTests.user)

    def post_exist(self, page_context):
        """Метод для проверки существования поста на страницах"""
        if "page_obj" in page_context:
            post = page_context["page_obj"][0]
        else:
            post = page_context["post"]
        author = post.author
        group = post.group
        text = post.text
        self.assertEqual(author, self.post.author)
        self.assertEqual(group, self.post.group)
        self.assertEqual(text, self.post.text)

    def test_index(self):
        """
           Список постов в шаблоне index,
           равен ожидаемому контексту.
        """

        response = self.guest_client.get(reverse("posts:index"))
        context = response.context
        self.post_exist(context)

    def test_group_list(self):
        """Список постов в шаблоне group_list равен ожидаемому контексту."""
        response = self.guest_client.get(
            reverse("posts:group_list", kwargs={"slug": self.group.slug})
        )
        context = response.context
        group = response.context["group"]
        self.post_exist(context)
        self.assertEqual(group, self.group)

    def test_profile(self):
        """Список постов в шаблоне profile равен ожидаемому контексту."""
        response = self.guest_client.get(
            reverse("posts:profile", kwargs={"username": self.post.author})
        )
        context = response.context
        profile = response.context["author"]
        self.post_exist(context)
        self.assertEqual(profile, self.user)

    def test_post_detail(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse("posts:post_detail", kwargs={"post_id": self.post.id})
        )
        context = response.context
        post = response.context["post"]
        self.post_exist(context)
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group, self.post.group)

    def test_create_edit(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse("posts:post_edit", kwargs={"post_id": self.post.id})
        )
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context["form"].fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_create(self):
        """Шаблон create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse("posts:post_create"))
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context["form"].fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_check_group_in_pages(self):
        """Проверьте, что если при создании поста указать группу, то этот пост
        появляется на главной странице, в выбранной группе, в профайле"""
        page_fields = {
            reverse("posts:index"):
                Post.objects.get(group=self.post.group),
            reverse("posts:group_list", kwargs={"slug": self.group.slug}):
                Post.objects.get(group=self.post.group),
            reverse("posts:profile", kwargs={"username": self.post.author}):
                Post.objects.get(group=self.post.group),
        }
        for value, expected in page_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                page_obj = response.context["page_obj"]
                self.assertIn(expected, page_obj)

    def test_check_group_not_in_mistake_group_list_page(self):
        """ Проверьте, что этот пост не попал в группу, для которой не был
        предназначен."""
        page_fields = {
            reverse("posts:group_list", kwargs={"slug": self.group.slug}):
            Post.objects.exclude(group=self.post.group),
        }
        for value, expected in page_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                page_obj = response.context["page_obj"]
                self.assertNotIn(expected, page_obj)

    def test_comment(self):
        """Только авторизованный и коммент появляется на стринце поста"""
        comments_count = Comment.objects.count()
        form_data = {
            "author": self.user,
            "text": "Текстовый комментарий"
        }
        response = self.authorized_client.post(
            reverse("posts:add_comment", kwargs={"post_id": self.post.id}),
            data=form_data,
            follow=True
        )
        comment = Comment.objects.last()
        self.assertRedirects(
            response,
            reverse("posts:post_detail", kwargs={"post_id": self.post.id})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(comment.text, form_data["text"])
        self.assertEqual(comment.author, self.user)

    def test_cache(self):
        """Проверка  кэша"""
        response = self.guest_client.get(reverse("posts:index")).content
        Post.objects.create(
            text="Пост ",
            author=self.user,
        )
        response_1 = self.guest_client.get(reverse("posts:index")).content
        self.assertEqual(response, response_1)

    def test_cache_changes(self):
        response = self.guest_client.get(reverse("posts:index")).content
        Post.objects.create(
            text="Пост ",
            author=self.user,
        )
        cache.clear()
        response_1 = self.guest_client.get(reverse("posts:index")).content
        self.assertNotEqual(response, response_1)


class PaginatorTest(TestCase):
    """Шаблон индекс  профайл  и группы с корректным паджинатором"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cache.clear()
        cls.user = User.objects.create_user(username="leo")
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test",
            description="Что-то о группе",
        )

    def test_paginator_on_pages(self):
        """Проверяем, что первые страницы возвращают 10 постов, вторые 8"""
        Post.objects.bulk_create(
            Post(
                author=self.user,
                text=f"Текст поста + {posts}",
                group=self.group,
            )
            for posts in range(1, 19)
        )
        first_pages = 10
        second_pages = 8
        context = {
            reverse("posts:index"): first_pages,
            reverse("posts:index") + "?page=2": second_pages,
            reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ): first_pages,
            reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ) + "?page=2": second_pages,
            reverse(
                "posts:profile", kwargs={"username": self.user.username}
            ): first_pages,
            reverse(
                "posts:profile", kwargs={"username": self.user.username}
            ) + "?page=2": second_pages,
        }

        for key, value in context.items():
            with self.subTest(key=key):
                response_page = self.guest_client.get(key)
                self.assertEqual(len(response_page.context["page_obj"]), value)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="auth")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Что-то о группе",
        )
        cls.small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        cls.image = SimpleUploadedFile(
            name="small.gif",
            content=cls.small_gif,
            content_type="image/gif"
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text="Текст поста",
            group=cls.group,
            image=cls.image
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        cache.clear()

    def test_image_index_group_profile(self):
        """Картинка передается на главную страницу, профайл, группу"""
        templates = (
            reverse("posts:index"),
            reverse("posts:profile", kwargs={"username": self.post.author}),
            reverse("posts:group_list", kwargs={"slug": self.group.slug}),
        )
        for key in templates:
            with self.subTest(key):
                response = self.guest_client.get(key)
                page_obj = response.context["page_obj"][0]
                self.assertEqual(page_obj.image, self.post.image)

    def test_image_post_detail(self):
        """Картинка передается на отдельную страницу поста"""
        response = self.guest_client.get(
            reverse("posts:post_detail", kwargs={"post_id": self.post.id})
        )
        post = response.context["post"]
        self.assertEqual(post.image, self.post.image)


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="auth")
        cls.post = Post.objects.create(
            author=cls.user,
            text="Текст поста",
        )
        cls.follower = User.objects.create_user(username="follower")

    def setUp(self):
        cache.clear()
        self.follower_client = Client()
        self.follower_client.force_login(self.follower)
        self.user_client = Client()
        self.user_client.force_login(self.user)

    def test_follow(self):
        """Подписаться"""
        response = self.follower_client.get(reverse("posts:follow_index"))
        page_obj = response.context["page_obj"]
        self.assertEqual(len(page_obj), Follow.objects.count())
        self.follower_client.get(
            reverse(
                "posts:profile_follow",
                kwargs={"username": self.user.username}
            )
        )
        response = self.follower_client.get(reverse("posts:follow_index"))
        page_obj = response.context["page_obj"]
        self.assertEqual(len(page_obj), Follow.objects.count())
        page_obj = response.context["page_obj"][0]
        self.assertEqual(page_obj.author, self.user)
        self.assertEqual(page_obj.text, self.post.text)
        self.assertTrue(
            Follow.objects.filter(
                user=self.follower,
                author=self.user
            ).exists()
        )

    def test_unfollow(self):
        """Отписаться"""
        self.follower_client.get(
            reverse(
                "posts:profile_unfollow",
                kwargs={"username": self.user.username}
            )
        )
        response = self.follower_client.get(reverse("posts:follow_index"))
        page_obj = response.context["page_obj"]
        self.assertEqual(len(page_obj), Follow.objects.count())
        self.assertFalse(
            Follow.objects.filter(
                user=self.follower,
                author=self.user
            ).exists()
        )

    def test_show_post_follow(self):
        self.follower_client.get(
            reverse(
                "posts:profile_unfollow",
                kwargs={"username": self.user.username}
            )
        )
        response = self.follower_client.get(reverse("posts:follow_index"))
        page_obj = response.context["page_obj"]
        self.assertEqual(len(page_obj), Follow.objects.count())

    def test_not_show_post(self):
        response = self.follower_client.get(reverse("posts:follow_index"))
        page_obj = response.context["page_obj"]
        self.assertEqual(len(page_obj), Follow.objects.count())
