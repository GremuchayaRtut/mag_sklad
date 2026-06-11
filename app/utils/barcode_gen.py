import random
import uuid


def generate_internal_barcode(business_id: uuid.UUID) -> str:
    """Return a 13-digit EAN-13-compatible internal barcode.

    Prefix 2 is reserved for store/internal use by the EAN-13 standard.
    Format: 2 + last-6-hex-digits-of-business-id + 6-random-digits
    """
    business_suffix = str(business_id).replace("-", "")[-6:]
    random_part = "".join(str(random.randint(0, 9)) for _ in range(6))
    return f"2{business_suffix}{random_part}"
