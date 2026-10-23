from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Task


class TaskApiTests(APITestCase):
    def setUp(self):
        get_user_model().objects.create_user("demo", password="clave-de-prueba-123")
        self.task = Task.objects.create(title="Existente")

    def login(self):
        r = self.client.post("/api/token/", {"username": "demo", "password": "clave-de-prueba-123"})
        self.assertEqual(r.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def test_anonimo_puede_consultar(self):
        self.assertEqual(self.client.get("/api/tasks/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/tasks/{self.task.id}/").status_code, 200)

    def test_anonimo_no_puede_modificar(self):
        self.assertEqual(self.client.post("/api/tasks/", {"title": "x"}).status_code, 401)
        self.assertEqual(self.client.patch(f"/api/tasks/{self.task.id}/", {"completed": True}).status_code, 401)
        self.assertEqual(self.client.delete(f"/api/tasks/{self.task.id}/").status_code, 401)

    def test_login_invalido(self):
        r = self.client.post("/api/token/", {"username": "demo", "password": "mala"})
        self.assertEqual(r.status_code, 401)

    def test_crud_autenticado(self):
        self.login()
        r = self.client.post("/api/tasks/", {"title": "Nueva"})
        self.assertEqual(r.status_code, 201)
        tid = r.data["id"]
        r = self.client.patch(f"/api/tasks/{tid}/", {"completed": True}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["completed"])
        self.assertEqual(self.client.delete(f"/api/tasks/{tid}/").status_code, 204)
        self.assertEqual(self.client.get(f"/api/tasks/{tid}/").status_code, 404)

    def test_datos_invalidos(self):
        self.login()
        self.assertEqual(self.client.post("/api/tasks/", {"title": ""}).status_code, 400)
        self.assertEqual(self.client.post("/api/tasks/", {"title": "x" * 101}).status_code, 400)
