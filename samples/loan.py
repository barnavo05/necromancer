"""Python translation of LOAN (months to repay a loan)."""
from decimal import Decimal, ROUND_DOWN, getcontext

getcontext().prec = 50
CENTS = Decimal("0.01")


def main(lines):
    amount = Decimal(lines[0])   # PIC 9(7)V99
    rate = Decimal(lines[1])     # PIC 9(2)V99
    payment = Decimal(lines[2])  # PIC 9(7)V99

    balance = amount
    months = 0
    paid = Decimal(0)

    # PERFORM MONTH-PARA UNTIL WS-BALANCE = 0 OR WS-MONTHS >= 360
    while not (balance == 0 or months >= 360):
        # COMPUTE truncates to cents when stored into PIC 9(8)V99
        interest = (balance * rate / 1200).quantize(CENTS, rounding=ROUND_DOWN)
        balance += interest
        if payment >= balance:
            paid += balance
            balance = Decimal(0)
        else:
            paid += payment
            balance -= payment
        months += 1

    status = "REPAID" if balance == 0 else "TOOLONG"
    return [f"MONTHS={months:03d}", f"PAID={paid:012.2f}", f"STATUS={status}"]
