"""
Polpoo API Client
Recibe credenciales por petición — sin estado, sin caché compartido entre clientes.
Cada instancia gestiona su propio token de forma aislada.
"""
import httpx
from datetime import datetime, timedelta

BASE_URL = "https://v2.restapi.polpoo.com/api"
CLIENT_ID = 1
CLIENT_SECRET = "tT96kecNtYVf92dvRfQ1Ikj6sjsx5tKZzaCCpHun"


class PolpooClient:
    def __init__(self, username: str, password: str):
        if not username or not password:
            raise ValueError("Usuario y contraseña de Polpoo son requeridos")
        self.username = username
        self.password = password
        # Token de integración (rutas, tracking, clientes, etc.)
        self._token: str | None = None
        self._token_expires_at: datetime | None = None
        # Token admin (usuarios, etc.)
        self._admin_token: str | None = None
        self._admin_token_expires_at: datetime | None = None

    async def get_token(self) -> str:
        """Token de integración — para rutas, albaranes, tracking, etc."""
        if self._token and self._token_expires_at and datetime.now() < self._token_expires_at:
            return self._token

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{BASE_URL}/oauth/token_integrator",
                json={
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "username": self.username,
                    "password": self.password,
                    "grant_type": "password",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            self._token_expires_at = datetime.now() + timedelta(seconds=data["expires_in"] - 300)
            return self._token

    async def get_admin_token(self) -> str:
        """Token admin — para endpoints de usuarios y administración."""
        if self._admin_token and self._admin_token_expires_at and datetime.now() < self._admin_token_expires_at:
            return self._admin_token

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{BASE_URL}/oauth/token_admin",
                json={
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "username": self.username,
                    "password": self.password,
                    "grant_type": "password",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._admin_token = data["access_token"]
            self._admin_token_expires_at = datetime.now() + timedelta(seconds=data["expires_in"] - 300)
            return self._admin_token

    async def _headers(self) -> dict:
        token = await self.get_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def _admin_headers(self) -> dict:
        token = await self.get_admin_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def enviar_rutas(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{BASE_URL}/integration_session/delivery_point", json=payload, headers=await self._headers())
            return resp.json()

    async def enviar_albaranes(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{BASE_URL}/route/route_planning_route/albaran_file", json=payload, headers=await self._headers())
            return resp.json()

    async def enviar_cobros(self, bills: list) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{BASE_URL}/company_bill_upload", json={"bills": bills}, headers=await self._headers())
            return resp.json()

    async def consultar_cobros(self, delivery_point_id: str = None, code: str = None) -> dict:
        body = {}
        if delivery_point_id: body["deliveryPointId"] = delivery_point_id
        if code: body["code"] = code
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{BASE_URL}/payments", json=body, headers=await self._headers())
            return resp.json()

    async def obtener_orden_rutas(self, date: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{BASE_URL}/integration/route/planified", json={"date": date}, headers=await self._headers())
            return resp.json()

    async def seguimiento_rutas(self, date: str, order_number: str = None, route_id: str = None, client_id: str = None) -> dict:
        params = {}
        if order_number: params["orderNumber"] = order_number
        if route_id: params["routeId"] = route_id
        if client_id: params["id"] = client_id
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{BASE_URL}/route/route_planning_route/date/{date}/delivery_points", params=params, headers=await self._headers())
            return resp.json()

    async def geolocalizacion_chofer(self, order_number: str = None, name: str = None, username: str = None) -> dict:
        body = {}
        if order_number: body["orderNumber"] = order_number
        if name: body["name"] = name
        if username: body["userName"] = username
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{BASE_URL}/driver/geolocation", json=body, headers=await self._headers())
            return resp.json()

    async def maestro_clientes(self, client_id: str = None, name: str = None) -> dict:
        params = {}
        if client_id: params["id"] = client_id
        if name: params["name"] = name
        async with httpx.AsyncClient(timeout=30) as http_client:
            resp = await http_client.get(f"{BASE_URL}/delivery_point_datatables", params=params, headers=await self._headers())
            return resp.json()

    async def tracking_evento(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{BASE_URL}/integration/tracking", json=payload, headers=await self._headers())
            return resp.json()

    async def verificar_permiso_crear_usuarios(self) -> dict:
        """Comprueba si el usuario autenticado tiene permisos para crear nuevos usuarios."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{BASE_URL}/can_add_users_subscription",
                headers=await self._admin_headers(),
            )
            return resp.json()

    async def tipos_usuario(self) -> dict:
        """Devuelve los tipos de usuario disponibles (Empleado, Autónomo, etc.) con fechas de creación."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{BASE_URL}/user_type",
                json={},
                headers=await self._admin_headers(),
            )
            return resp.json()

    async def totalizadores_usuarios(self) -> dict:
        """Devuelve totales de usuarios: activos, inactivos y por tipología."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{BASE_URL}/user_totalized",
                json={},
                headers=await self._admin_headers(),
            )
            return resp.json()

    async def listar_usuarios(self, show_active: bool = True) -> dict:
        """Lista usuarios de la cuenta Polpoo."""
        params = {
            "me": "true",
            "showActive": "true" if show_active else "false",
        }
        async with httpx.AsyncClient(timeout=30) as http_client:
            resp = await http_client.get(
                f"{BASE_URL}/users_datatables",
                params=params,
                headers=await self._admin_headers(),
            )
            return resp.json()
