       IDENTIFICATION DIVISION.
       PROGRAM-ID. BALANCE.
      *> Difference between the amount paid and the amount owed.
      *> Input (stdin, one value per line, plain decimal text):
      *>   amount paid, amount owed
      *> The difference is stored in an UNSIGNED field, so a negative
      *> result is stored as its absolute value.
      *> Output: difference, status
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-LINE           PIC X(20).
       01 WS-PAID           PIC 9(4)V99.
       01 WS-OWED           PIC 9(4)V99.
       01 WS-DIFF           PIC 9(4)V99.
       01 WS-DIFF-OUT       PIC 9(4).99.
       PROCEDURE DIVISION.
       MAIN-PARA.
           ACCEPT WS-LINE
           COMPUTE WS-PAID = FUNCTION NUMVAL(WS-LINE)
           ACCEPT WS-LINE
           COMPUTE WS-OWED = FUNCTION NUMVAL(WS-LINE)
           COMPUTE WS-DIFF = WS-PAID - WS-OWED
           MOVE WS-DIFF TO WS-DIFF-OUT
           DISPLAY "DIFF=" WS-DIFF-OUT
           IF WS-PAID >= WS-OWED
               DISPLAY "STATUS=SETTLED"
           ELSE
               DISPLAY "STATUS=OWING"
           END-IF
           STOP RUN.
