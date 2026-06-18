"""
Herramientas del chatbot (CU-18, Fase 1). Cada una reutiliza los servicios del
modulo product (no duplica consultas) y devuelve TEXTO listo para el modelo.

Son agnosticas del proveedor: la misma lista de Tool funciona con cualquier
implementacion de IChatModel.
"""
from chatbot.interfaces import Tool
from product.exceptions import ProductoNoEncontradoError
from product.service import BusquedaService, CatalogoService, CategoriaService

_MAX_RESULTADOS = 8  # cuantos productos listar como maximo en una respuesta


def construir_tools(
    busqueda: BusquedaService,
    categoria: CategoriaService,
    catalogo: CatalogoService,
) -> list[Tool]:
    def buscar_productos(consulta: str) -> str:
        resultado = busqueda.buscar(consulta, None, 1)
        if not resultado.productos:
            return f"No se encontraron productos para '{consulta}'."
        lineas = [f"Se encontraron {resultado.total} producto(s) para '{consulta}':"]
        for p in resultado.productos[:_MAX_RESULTADOS]:
            precio = f"₡{p.precio_actual:,.0f}"
            if p.en_oferta and p.precio_original is not None:
                lineas.append(
                    f"- [{p.codigo}] {p.nombre} — {precio} "
                    f"(oferta, antes ₡{p.precio_original:,.0f})"
                )
            else:
                lineas.append(f"- [{p.codigo}] {p.nombre} — {precio}")
        return "\n".join(lineas)

    def listar_categorias() -> str:
        categorias = categoria.obtener_categorias()
        if not categorias:
            return "No hay categorias disponibles por el momento."
        return "Categorias disponibles: " + ", ".join(c.nombre for c in categorias)

    def detalle_producto(codigo: str) -> str:
        try:
            d = catalogo.obtener_detalle(codigo)
        except ProductoNoEncontradoError:
            return f"No existe un producto con codigo '{codigo}'."
        partes = [f"{d.nombre} (codigo {d.codigo})"]
        if d.categoria is not None:
            partes.append(f"Categoria: {d.categoria.nombre}")
        precio = f"Precio: ₡{d.precio_actual:,.0f}"
        if d.en_oferta and d.precio_original is not None:
            precio += f" (oferta, antes ₡{d.precio_original:,.0f})"
        partes.append(precio)
        if d.descripcion:
            partes.append(f"Descripcion: {d.descripcion}")
        return "\n".join(partes)

    return [
        Tool(
            name="buscar_productos",
            description=(
                "Busca productos del catalogo por nombre o palabra clave. "
                "Devuelve nombre, codigo y precio de cada coincidencia."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "consulta": {
                        "type": "string",
                        "description": "Texto a buscar, por ejemplo 'pala', 'abono', 'manguera'.",
                    }
                },
                "required": ["consulta"],
            },
            func=buscar_productos,
        ),
        Tool(
            name="listar_categorias",
            description="Lista las categorias de productos disponibles en la tienda.",
            parameters={"type": "object", "properties": {}},
            func=listar_categorias,
        ),
        Tool(
            name="detalle_producto",
            description=(
                "Obtiene el detalle completo de un producto (descripcion, categoria, "
                "precio) a partir de su codigo."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "codigo": {
                        "type": "string",
                        "description": "Codigo del producto, por ejemplo 'P001'.",
                    }
                },
                "required": ["codigo"],
            },
            func=detalle_producto,
        ),
    ]
