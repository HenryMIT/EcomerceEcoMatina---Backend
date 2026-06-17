"""
Generacion del PDF de factura/comprobante a partir de los datos del pedido.

OJO (arquitectura): la factura FISCAL (Hacienda) se emite en la app de escritorio
(violette_db). Este PDF es el comprobante de compra que la tienda web envia al
cliente al confirmarse el pago; no sustituye la factura electronica fiscal.

Usa fpdf2 (fuentes core, latin-1). Por eso los montos se prefijan con "CRC"
en vez del simbolo de colon (no representable en latin-1).
"""
from datetime import datetime
from decimal import Decimal

from fpdf import FPDF

from schemas_payment import LineaFactura

EMPRESA = "AgroMatina Ferreteria"


def _money(valor: Decimal) -> str:
    """Formatea un monto como 'CRC 12,500.00'."""
    return f"CRC {valor:,.2f}"


def generar_factura_pdf(
    codigo_pedido: str,
    cliente_nombre: str,
    cliente_correo: str,
    lineas: list[LineaFactura],
    total: Decimal,
) -> bytes:
    """Construye el PDF del comprobante y lo devuelve como bytes."""
    pdf = FPDF()
    pdf.add_page()

    # ── Encabezado ───────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, EMPRESA, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "Comprobante de compra", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Datos del pedido ─────────────────────────────────────────────────────
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Numero de orden: {codigo_pedido}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Fecha: {fecha}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Cliente: {cliente_nombre}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Correo: {cliente_correo}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Tabla de detalle ─────────────────────────────────────────────────────
    col = (90.0, 25.0, 35.0, 40.0)  # producto, cantidad, precio, subtotal
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(45, 106, 79)  # verde AgroMatina
    pdf.set_text_color(255, 255, 255)
    pdf.cell(col[0], 8, "Producto", border=1, fill=True)
    pdf.cell(col[1], 8, "Cant.", border=1, align="R", fill=True)
    pdf.cell(col[2], 8, "P. Unit.", border=1, align="R", fill=True)
    pdf.cell(col[3], 8, "Subtotal", border=1, align="R", fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    for linea in lineas:
        nombre = linea.producto_nombre
        if len(nombre) > 55:
            nombre = nombre[:52] + "..."
        cantidad = f"{linea.cantidad:g}"
        pdf.cell(col[0], 8, nombre, border=1)
        pdf.cell(col[1], 8, cantidad, border=1, align="R")
        pdf.cell(col[2], 8, _money(linea.precio_unitario), border=1, align="R")
        pdf.cell(col[3], 8, _money(linea.subtotal), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    # ── Total ────────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(col[0] + col[1] + col[2], 9, "TOTAL", border=1, align="R")
    pdf.cell(col[3], 9, _money(total), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        0,
        5,
        "Gracias por su compra. Este comprobante corresponde a su pedido en la tienda "
        "en linea de AgroMatina. La factura electronica fiscal se emite por separado.",
    )

    return bytes(pdf.output())
