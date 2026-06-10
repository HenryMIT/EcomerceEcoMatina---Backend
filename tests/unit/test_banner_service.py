"""
Pruebas unitarias del RF-03 — BannerService aislado.

Repositorio falso (cumple IBannerRepository). El ORDEN por 'orden' es
responsabilidad del repositorio (ORDER BY) y se valida en integracion; aqui se
prueba el mapeo, el limite que pasa el servicio y los campos opcionales.
"""
from __future__ import annotations

from product.models import Banner
from product.schemas import BannerRead
from product.service import MAX_BANNERS, BannerService


class _FakeBannerRepository:
    def __init__(self, banners: list[Banner]) -> None:
        self._banners = banners
        self.limite_recibido: int | None = None

    def listar_activos(self, limite: int) -> list[Banner]:
        self.limite_recibido = limite
        return list(self._banners[:limite])


def _banner(
    imagen_url: str = "https://cdn/b1.jpg",
    texto: str | None = "Promo",
    url_destino: str | None = "/categories/CAT-HER/products",
) -> Banner:
    return Banner(
        imagen_url=imagen_url,
        texto_descriptivo=texto,
        url_destino=url_destino,
        activo=1,
        orden=0,
    )


def test_obtener_banners_lista_vacia() -> None:
    service = BannerService(_FakeBannerRepository([]))
    assert service.obtener_banners() == []


def test_obtener_banners_pasa_limite_maximo() -> None:
    repo = _FakeBannerRepository([])
    BannerService(repo).obtener_banners()
    assert repo.limite_recibido == MAX_BANNERS == 5


def test_obtener_banners_mapea_campos() -> None:
    service = BannerService(_FakeBannerRepository([_banner(
        imagen_url="https://cdn/promo.jpg",
        texto="Ofertas de temporada",
        url_destino="/categories/CAT-PIN/products",
    )]))

    salida = service.obtener_banners()

    assert len(salida) == 1
    dto = salida[0]
    assert isinstance(dto, BannerRead)
    assert dto.imagen_url == "https://cdn/promo.jpg"
    assert dto.texto_descriptivo == "Ofertas de temporada"
    assert dto.url_destino == "/categories/CAT-PIN/products"


def test_obtener_banners_campos_opcionales_none() -> None:
    service = BannerService(_FakeBannerRepository([_banner(texto=None, url_destino=None)]))

    dto = service.obtener_banners()[0]

    assert dto.texto_descriptivo is None
    assert dto.url_destino is None


def test_obtener_banners_preserva_orden_del_repositorio() -> None:
    banners = [_banner(imagen_url="a.jpg"), _banner(imagen_url="b.jpg"), _banner(imagen_url="c.jpg")]
    service = BannerService(_FakeBannerRepository(banners))

    urls = [b.imagen_url for b in service.obtener_banners()]

    assert urls == ["a.jpg", "b.jpg", "c.jpg"]
