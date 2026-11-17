       IDENTIFICATION DIVISION.
       PROGRAM-ID. INTEREST.
      *> Compound interest on a deposit, compounded once per year.
      *> Input (stdin, one value per line, plain decimal text such as 35.79):
      *>   principal, annual rate %, years
      *> Each line is read as text and converted with FUNCTION NUMVAL.
      *> Output (stdout): final balance and total interest earned
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-LINE           PIC X(20).
       01 WS-PRINCIPAL      PIC 9(7)V99.
       01 WS-RATE           PIC 9(2)V99.
       01 WS-YEARS          PIC 9(2).
       01 WS-BALANCE        PIC 9(9)V99.
       01 WS-INTEREST       PIC 9(9)V99.
       01 WS-YEAR-COUNTER   PIC 9(2).
       01 WS-BALANCE-OUT    PIC 9(9).99.
       01 WS-INTEREST-OUT   PIC 9(9).99.
       PROCEDURE DIVISION.
       MAIN-PARA.
           ACCEPT WS-LINE
           COMPUTE WS-PRINCIPAL = FUNCTION NUMVAL(WS-LINE)
           ACCEPT WS-LINE
           COMPUTE WS-RATE = FUNCTION NUMVAL(WS-LINE)
           ACCEPT WS-LINE
           COMPUTE WS-YEARS = FUNCTION NUMVAL(WS-LINE)
           MOVE WS-PRINCIPAL TO WS-BALANCE
           PERFORM COMPOUND-PARA
               VARYING WS-YEAR-COUNTER FROM 1 BY 1
               UNTIL WS-YEAR-COUNTER > WS-YEARS
           COMPUTE WS-INTEREST = WS-BALANCE - WS-PRINCIPAL
           MOVE WS-BALANCE TO WS-BALANCE-OUT
           MOVE WS-INTEREST TO WS-INTEREST-OUT
           DISPLAY "BALANCE=" WS-BALANCE-OUT
           DISPLAY "INTEREST=" WS-INTEREST-OUT
           STOP RUN.
       COMPOUND-PARA.
           COMPUTE WS-BALANCE = WS-BALANCE * (1 + WS-RATE / 100).
