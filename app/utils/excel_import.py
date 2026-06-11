import io
from decimal import Decimal, InvalidOperation

import openpyxl

from app.core.exceptions import BadRequestError
from app.models.enums import Unit

_VALID_UNITS = {u.value for u in Unit}


def parse_products_excel(file_bytes: bytes) -> list[dict]:
    """Parse an .xlsx file and return a list of raw product dicts.

    Expected columns (row 1 = header, data from row 2):
      A: name          (required)
      B: barcode       (optional)
      C: unit          (pcs/kg/l/m/pack — defaults to pcs if unrecognised)
      D: category      (optional string)
      E: sale_price    (required numeric)
      F: purchase_price(optional numeric, defaults to 0)
      G: min_stock     (optional int, defaults to 0)
    """
    try:
        wb = openpyxl.load_workbook(
            io.BytesIO(file_bytes), read_only=True, data_only=True
        )
        ws = wb.active
    except Exception as exc:
        raise BadRequestError(f"Cannot read Excel file: {exc}") from exc

    rows = list(ws.iter_rows(min_row=2, values_only=True))
    if not rows:
        raise BadRequestError("Excel file has no data rows")

    products: list[dict] = []

    for row in rows:
        # Pad to at least 7 columns so index access is always safe
        cells = list(row) + [None] * 7

        name_raw = cells[0]
        barcode_raw = cells[1]
        unit_raw = cells[2]
        category_raw = cells[3]
        sale_price_raw = cells[4]
        purchase_price_raw = cells[5]
        min_stock_raw = cells[6]

        # Skip rows that lack required fields
        if not name_raw or sale_price_raw is None:
            continue

        name = str(name_raw).strip()
        if not name:
            continue

        try:
            sale_price = Decimal(str(sale_price_raw))
        except InvalidOperation:
            continue  # unparseable price → skip row

        try:
            purchase_price = (
                Decimal(str(purchase_price_raw))
                if purchase_price_raw is not None
                else Decimal("0")
            )
        except InvalidOperation:
            purchase_price = Decimal("0")

        unit_str = str(unit_raw).strip().lower() if unit_raw else "pcs"
        unit = unit_str if unit_str in _VALID_UNITS else "pcs"

        try:
            min_stock = int(min_stock_raw) if min_stock_raw is not None else 0
        except (ValueError, TypeError):
            min_stock = 0

        products.append(
            {
                "name": name,
                "barcode": str(barcode_raw).strip() if barcode_raw else None,
                "unit": unit,
                "category": str(category_raw).strip() if category_raw else None,
                "sale_price": sale_price,
                "purchase_price": purchase_price,
                "min_stock": min_stock,
            }
        )

    if not products:
        raise BadRequestError("No valid product rows found in the Excel file")

    return products
