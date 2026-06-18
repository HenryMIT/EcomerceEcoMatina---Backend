"""Pruebas de las herramientas del chatbot — los servicios de product se mockean."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from chatbot.tools import construir_tools
from product.exceptions import ProductoNoEncontradoError


def _tool(tools, nombre):
    return next(t for t in tools if t.name == nombre)


def test_buscar_productos_formatea_resultados():
    busqueda = MagicMock()
    busqueda.buscar.return_value = SimpleNamespace(
        total=2,
        productos=[
            SimpleNamespace(
                codigo="P001", nombre="Pala de jardin",
                precio_actual=Decimal("3500"), en_oferta=False, precio_original=None,
            ),
            SimpleNamespace(
                codigo="P002", nombre="Saco de abono",
                precio_actual=Decimal("12500"), en_oferta=True, precio_original=Decimal("14000"),
            ),
        ],
    )
    tools = construir_tools(busqueda, MagicMock(), MagicMock())

    salida = _tool(tools, "buscar_productos").func(consulta="pala")

    assert "P001" in salida and "Pala de jardin" in salida
    assert "oferta" in salida  # el segundo esta en oferta
    busqueda.buscar.assert_called_once_with("pala", None, 1)


def test_buscar_productos_sin_resultados():
    busqueda = MagicMock()
    busqueda.buscar.return_value = SimpleNamespace(total=0, productos=[])
    tools = construir_tools(busqueda, MagicMock(), MagicMock())

    salida = _tool(tools, "buscar_productos").func(consulta="xyz")

    assert "No se encontraron productos" in salida


def test_listar_categorias():
    categoria = MagicMock()
    categoria.obtener_categorias.return_value = [
        SimpleNamespace(nombre="Herramientas"),
        SimpleNamespace(nombre="Abonos"),
    ]
    tools = construir_tools(MagicMock(), categoria, MagicMock())

    salida = _tool(tools, "listar_categorias").func()

    assert "Herramientas" in salida and "Abonos" in salida


def test_detalle_producto_inexistente():
    catalogo = MagicMock()
    catalogo.obtener_detalle.side_effect = ProductoNoEncontradoError("no existe")
    tools = construir_tools(MagicMock(), MagicMock(), catalogo)

    salida = _tool(tools, "detalle_producto").func(codigo="ZZZ")

    assert "No existe un producto" in salida


def test_las_tres_tools_estan_declaradas():
    tools = construir_tools(MagicMock(), MagicMock(), MagicMock())
    nombres = {t.name for t in tools}
    assert nombres == {"buscar_productos", "listar_categorias", "detalle_producto"}
