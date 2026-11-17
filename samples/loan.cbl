       IDENTIFICATION DIVISION.
       PROGRAM-ID. LOAN.
      *> Months needed to repay a loan with a fixed monthly payment.
      *> Input (stdin, one value per line, plain decimal text):
      *>   loan amount, annual rate %, monthly payment
      *> Interest accrues monthly at rate / 12 percent, truncated to cents.
      *> Gives up after 360 months. Output: months, total paid, status
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-LINE           PIC X(20).
       01 WS-AMOUNT         PIC 9(7)V99.
       01 WS-RATE           PIC 9(2)V99.
       01 WS-PAYMENT        PIC 9(7)V99.
       01 WS-BALANCE        PIC 9(8)V99.
       01 WS-INTEREST       PIC 9(8)V99.
       01 WS-MONTHS         PIC 9(3) VALUE 0.
       01 WS-PAID           PIC 9(9)V99 VALUE 0.
       01 WS-MONTHS-OUT     PIC 9(3).
       01 WS-PAID-OUT       PIC 9(9).99.
       01 WS-STATUS         PIC X(8).
       PROCEDURE DIVISION.
       MAIN-PARA.
           ACCEPT WS-LINE
           COMPUTE WS-AMOUNT = FUNCTION NUMVAL(WS-LINE)
           ACCEPT WS-LINE
           COMPUTE WS-RATE = FUNCTION NUMVAL(WS-LINE)
           ACCEPT WS-LINE
           COMPUTE WS-PAYMENT = FUNCTION NUMVAL(WS-LINE)
           MOVE WS-AMOUNT TO WS-BALANCE
           PERFORM MONTH-PARA
               UNTIL WS-BALANCE = 0 OR WS-MONTHS >= 360
           IF WS-BALANCE = 0
               MOVE "REPAID" TO WS-STATUS
           ELSE
               MOVE "TOOLONG" TO WS-STATUS
           END-IF
           MOVE WS-MONTHS TO WS-MONTHS-OUT
           MOVE WS-PAID TO WS-PAID-OUT
           DISPLAY "MONTHS=" WS-MONTHS-OUT
           DISPLAY "PAID=" WS-PAID-OUT
           DISPLAY "STATUS=" WS-STATUS
           STOP RUN.
       MONTH-PARA.
           COMPUTE WS-INTEREST = WS-BALANCE * WS-RATE / 1200
           ADD WS-INTEREST TO WS-BALANCE
           IF WS-PAYMENT >= WS-BALANCE
               ADD WS-BALANCE TO WS-PAID
               MOVE 0 TO WS-BALANCE
           ELSE
               ADD WS-PAYMENT TO WS-PAID
               SUBTRACT WS-PAYMENT FROM WS-BALANCE
           END-IF
           ADD 1 TO WS-MONTHS.
