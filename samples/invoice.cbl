       IDENTIFICATION DIVISION.
       PROGRAM-ID. INVOICE.
      *> Invoice total with a quantity discount tier and sales tax.
      *> Input (stdin, one value per line, plain decimal text):
      *>   quantity, unit price
      *> Discount tiers: 100 or more 15 percent, 50 or more 10 percent,
      *> 10 or more 5 percent, otherwise none.
      *> Tax is 8.25 percent of the discounted amount, ROUNDED to cents.
      *> Output: subtotal, discount, tax, total
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-LINE           PIC X(20).
       01 WS-QTY            PIC 9(3).
       01 WS-PRICE          PIC 9(4)V99.
       01 WS-RATE           PIC 9V99.
       01 WS-SUBTOTAL       PIC 9(7)V99.
       01 WS-DISCOUNT       PIC 9(7)V99.
       01 WS-NET            PIC 9(7)V99.
       01 WS-TAX            PIC 9(7)V99.
       01 WS-TOTAL          PIC 9(7)V99.
       01 WS-SUBTOTAL-OUT   PIC 9(7).99.
       01 WS-DISCOUNT-OUT   PIC 9(7).99.
       01 WS-TAX-OUT        PIC 9(7).99.
       01 WS-TOTAL-OUT      PIC 9(7).99.
       PROCEDURE DIVISION.
       MAIN-PARA.
           ACCEPT WS-LINE
           COMPUTE WS-QTY = FUNCTION NUMVAL(WS-LINE)
           ACCEPT WS-LINE
           COMPUTE WS-PRICE = FUNCTION NUMVAL(WS-LINE)
           COMPUTE WS-SUBTOTAL = WS-QTY * WS-PRICE
           PERFORM TIER-PARA
           COMPUTE WS-DISCOUNT = WS-SUBTOTAL * WS-RATE
           COMPUTE WS-NET = WS-SUBTOTAL - WS-DISCOUNT
           PERFORM TAX-PARA
           COMPUTE WS-TOTAL = WS-NET + WS-TAX
           MOVE WS-SUBTOTAL TO WS-SUBTOTAL-OUT
           MOVE WS-DISCOUNT TO WS-DISCOUNT-OUT
           MOVE WS-TAX TO WS-TAX-OUT
           MOVE WS-TOTAL TO WS-TOTAL-OUT
           DISPLAY "SUBTOTAL=" WS-SUBTOTAL-OUT
           DISPLAY "DISCOUNT=" WS-DISCOUNT-OUT
           DISPLAY "TAX=" WS-TAX-OUT
           DISPLAY "TOTAL=" WS-TOTAL-OUT
           STOP RUN.
       TIER-PARA.
           EVALUATE TRUE
               WHEN WS-QTY >= 100
                   MOVE 0.15 TO WS-RATE
               WHEN WS-QTY >= 50
                   MOVE 0.10 TO WS-RATE
               WHEN WS-QTY >= 10
                   MOVE 0.05 TO WS-RATE
               WHEN OTHER
                   MOVE 0 TO WS-RATE
           END-EVALUATE.
       TAX-PARA.
           COMPUTE WS-TAX ROUNDED = WS-NET * 0.0825.
