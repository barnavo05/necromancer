"""Python translation of INVOICE (quantity discount and sales tax).

COMPUTE without ROUNDED truncates, so those steps use ROUND_DOWN.
COMPUTE ... ROUNDED rounds half away from zero, which is ROUND_HALF_UP in Decimal.
"""
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, getcontext

getcontext().prec = 50
CENTS = Decimal("0.01")


def main(lines):
    qty = int(lines[0])         # PIC 9(3)
    price = Decimal(lines[1])   # PIC 9(4)V99

    subtotal = (qty * price).quantize(CENTS, rounding=ROUND_DOWN)

    # TIER-PARA: EVALUATE TRUE, first matching WHEN wins
    if qty >= 100:
        rate = Decimal("0.15")
    elif qty >= 50:
        rate = Decimal("0.10")
    elif qty >= 10:
        rate = Decimal("0.05")
    else:
        rate = Decimal("0")

    discount = (subtotal * rate).quantize(CENTS, rounding=ROUND_DOWN)
    net = subtotal - discount

    # TAX-PARA: COMPUTE ... ROUNDED
    tax = (net * Decimal("0.0825")).quantize(CENTS, rounding=ROUND_HALF_UP)

    total = net + tax
    return [
        f"SUBTOTAL={subtotal:010.2f}",
        f"DISCOUNT={discount:010.2f}",
        f"TAX={tax:010.2f}",
        f"TOTAL={total:010.2f}",
    ]
