"""Python translation of PAYROLL (weekly pay with overtime and tax)."""
from decimal import Decimal, ROUND_DOWN, getcontext

getcontext().prec = 50
CENTS = Decimal("0.01")


def money(value):
    # COBOL COMPUTE without ROUNDED truncates toward zero into PIC 9(7)V99
    return value.quantize(CENTS, rounding=ROUND_DOWN)


def main(lines):
    hours = Decimal(lines[0])  # PIC 9(3)V9
    rate = Decimal(lines[1])   # PIC 9(3)V99

    # SPLIT-HOURS-PARA
    if hours > 40:
        regular_hours = Decimal(40)
        ot_hours = hours - 40
    else:
        regular_hours = hours
        ot_hours = Decimal(0)

    # GROSS-PARA
    gross = money(regular_hours * rate + ot_hours * rate * Decimal("1.5"))

    # TAX-PARA
    if gross > 500:
        tax = money((gross - 500) * Decimal("0.20"))
    else:
        tax = Decimal(0)

    net = gross - tax
    return [f"GROSS={gross:010.2f}", f"TAX={tax:010.2f}", f"NET={net:010.2f}"]
