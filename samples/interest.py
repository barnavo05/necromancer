"""Python translation of INTEREST (compound interest).

Money uses Decimal, never float. COBOL COMPUTE without ROUNDED truncates
toward zero when storing into a PIC with fewer decimals, so we use ROUND_DOWN.
"""
from decimal import Decimal, ROUND_DOWN, getcontext

getcontext().prec = 50
CENTS = Decimal("0.01")


def main(lines):
    principal = Decimal(lines[0])  # PIC 9(7)V99 (read with NUMVAL)
    rate = Decimal(lines[1])       # PIC 9(2)V99
    years = int(lines[2])          # PIC 9(2)

    balance = principal            # MAIN-PARA: MOVE WS-PRINCIPAL TO WS-BALANCE
    for _ in range(years):         # PERFORM COMPOUND-PARA VARYING ... UNTIL > WS-YEARS
        balance = (balance * (1 + rate / 100)).quantize(CENTS, rounding=ROUND_DOWN)

    interest = balance - principal
    # PIC 9(9).99 edited output is 12 characters wide, zero-padded
    return [f"BALANCE={balance:012.2f}", f"INTEREST={interest:012.2f}"]
