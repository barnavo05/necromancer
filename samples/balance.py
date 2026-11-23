"""Python translation of BALANCE (difference between paid and owed)."""
from decimal import Decimal, getcontext

getcontext().prec = 50


def main(lines):
    paid = Decimal(lines[0])   # PIC 9(4)V99
    owed = Decimal(lines[1])   # PIC 9(4)V99

    # COMPUTE WS-DIFF = WS-PAID - WS-OWED, stored in an UNSIGNED field:
    # COBOL drops the minus sign, so a negative result is kept as its absolute value.
    diff = abs(paid - owed)

    status = "SETTLED" if paid >= owed else "OWING"
    return [f"DIFF={diff:07.2f}", f"STATUS={status}"]
