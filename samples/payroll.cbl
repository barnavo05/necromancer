       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYROLL.
      *> Weekly pay with overtime and a flat tax band.
      *> Input (stdin, one value per line, plain decimal text):
      *>   hours worked, hourly rate
      *> Hours over 40 are paid at 1.5 times the rate.
      *> Gross pay above 500.00 is taxed at 20 percent on the excess.
      *> Output: gross, tax, net
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-LINE           PIC X(20).
       01 WS-HOURS          PIC 9(3)V9.
       01 WS-RATE           PIC 9(3)V99.
       01 WS-REGULAR-HOURS  PIC 9(3)V9.
       01 WS-OT-HOURS       PIC 9(3)V9.
       01 WS-GROSS          PIC 9(7)V99.
       01 WS-TAX            PIC 9(7)V99.
       01 WS-NET            PIC 9(7)V99.
       01 WS-GROSS-OUT      PIC 9(7).99.
       01 WS-TAX-OUT        PIC 9(7).99.
       01 WS-NET-OUT        PIC 9(7).99.
       PROCEDURE DIVISION.
       MAIN-PARA.
           ACCEPT WS-LINE
           COMPUTE WS-HOURS = FUNCTION NUMVAL(WS-LINE)
           ACCEPT WS-LINE
           COMPUTE WS-RATE = FUNCTION NUMVAL(WS-LINE)
           PERFORM SPLIT-HOURS-PARA
           PERFORM GROSS-PARA
           PERFORM TAX-PARA
           COMPUTE WS-NET = WS-GROSS - WS-TAX
           MOVE WS-GROSS TO WS-GROSS-OUT
           MOVE WS-TAX TO WS-TAX-OUT
           MOVE WS-NET TO WS-NET-OUT
           DISPLAY "GROSS=" WS-GROSS-OUT
           DISPLAY "TAX=" WS-TAX-OUT
           DISPLAY "NET=" WS-NET-OUT
           STOP RUN.
       SPLIT-HOURS-PARA.
           IF WS-HOURS > 40
               MOVE 40 TO WS-REGULAR-HOURS
               COMPUTE WS-OT-HOURS = WS-HOURS - 40
           ELSE
               MOVE WS-HOURS TO WS-REGULAR-HOURS
               MOVE 0 TO WS-OT-HOURS
           END-IF.
       GROSS-PARA.
           COMPUTE WS-GROSS = WS-REGULAR-HOURS * WS-RATE
               + WS-OT-HOURS * WS-RATE * 1.5.
       TAX-PARA.
           IF WS-GROSS > 500
               COMPUTE WS-TAX = (WS-GROSS - 500) * 0.20
           ELSE
               MOVE 0 TO WS-TAX
           END-IF.
