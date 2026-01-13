"""Examples data"""
from typing import Dict

EXAMPLES: Dict[str, Dict[str, str]] = {
    "תרגולים - רמה 1": {
        "דוגמה 1: הדפס מספר": """; משימה: הדפס את המספר 42
MOV R1, 42
PRINT R1
HALT
""",
        "דוגמה 2: חיבור פשוט": """; משימה: חשב 10+20 והדפס
MOV R1, 10
ADD R1, 20
PRINT R1
HALT
""",
        "דוגמה 3: חיסור": """; משימה: חשב 50-15 והדפס
MOV R1, 50
SUB R1, 15
PRINT R1
HALT
""",
        "דוגמה 4: כפל": """; משימה: חשב 6*7 והדפס
MOV R1, 6
MUL R1, 7
PRINT R1
HALT
""",
        "דוגמה 5: העתקה": """; משימה: העתק 100 ל-R2 והדפס
MOV R1, 100
MOV R2, R1
PRINT R2
HALT
""",
        "דוגמה 6: מספר אקראי": """; משימה: הדפס מספר אקראי בין 0 ל-32
RAND R1
PRINT R1
HALT
""",
    },
    "תרגולים - רמה 2": {
        "דוגמה 1: סכום 1 עד 5": """; משימה: חשב סכום 1..5 והדפס
MOV R1, 0
MOV R2, 1
MOV L1, 5
LOOP_START:
ADD R1, R2
INC R2
LOOP LOOP_START
PRINT R1
HALT
""",
        "דוגמה 2: עצרת 5!": """; משימה: חשב 5! והדפס
MOV R1, 1
MOV R2, 5
MOV L1, 5
F:
MUL R1, R2
DEC R2
LOOP F
PRINT R1
HALT
""",
        "דוגמה 3: זוגי/אי זוגי": """; משימה: הדפס 0 אם זוגי, 1 אם אי-זוגי
MOV R1, 17
MOV R2, R1
MOD R2, 2
CMP R2, 0
JZ EVEN
MOV R3, 1
GOTO END
EVEN:
MOV R3, 0
END:
PRINT R3
HALT
""",
        "דוגמה 4: מחסנית הפוך": """; משימה: הדפס 3 מספרים בסדר הפוך בעזרת S1
MOV R1, 10
PUSH R1, S1
MOV R1, 20
PUSH R1, S1
MOV R1, 30
PUSH R1, S1
POP R1, S1
PRINT R1
POP R1, S1
PRINT R1
POP R1, S1
PRINT R1
HALT
""",
        "דוגמה 5: LIST קריאה/כתיבה": """; משימה: כתוב 99 ב-LIST[5] ואז הדפס אותו
MOV R1, 5
MOV [LIST+R1], 99
MOV R2, [LIST+R1]
PRINT R2
HALT
""",
        "דוגמה 6: השוואה": """; משימה: השווה 10 ל-5 והדפס 1 אם 10>5, אחרת 0
MOV R1, 10
MOV R2, 5
CMP R1, R2
IF R1 > R2 GOTO BIGGER
MOV R3, 0
GOTO END
BIGGER:
MOV R3, 1
END:
PRINT R3
HALT
""",
    },
    "תרגולים - רמה 3": {
        "דוגמה 1: סכום זוגיים": """; משימה: חשב סכום המספרים הזוגיים מ-2 עד 10
MOV R1, 0
MOV R2, 2
MOV L1, 5
LOOP_SUM:
ADD R1, R2
ADD R2, 2
LOOP LOOP_SUM
PRINT R1
HALT
""",
        "דוגמה 2: מקסימום": """; משימה: מצא את המקסימום בין 15 ל-23 והדפס
MOV R1, 15
MOV R2, 23
CMP R1, R2
IF R1 > R2 GOTO R1_BIGGER
MOV R3, R2
GOTO END
R1_BIGGER:
MOV R3, R1
END:
PRINT R3
HALT
""",
        "דוגמה 3: חילוק עם שארית": """; משימה: חשב 17/5 והדפס את המנה ואת השארית
MOV R1, 17
MOV R2, 5
MOV R3, R1
DIV R3, R2
PRINT R3
MOD R1, R2
PRINT R1
HALT
""",
        "דוגמה 4: LIST עם אינדקס דינמי": """; משימה: כתוב 100 ב-LIST[R1] כאשר R1=7 ואז הדפס
MOV R1, 7
MOV [LIST+R1], 100
MOV R2, [LIST+R1]
PRINT R2
HALT
""",
        "דוגמה 5: החלפת ערכים": """; משימה: החלף את הערכים של R1 ו-R2 והדפס את שניהם
MOV R1, 10
MOV R2, 20
SWAP R1, R2
PRINT R1
PRINT R2
HALT
""",
        "דוגמה 6: סכום עם מחסנית": """; משימה: חשב סכום 5+10+15 באמצעות מחסנית והדפס
MOV R1, 5
PUSH R1, S1
MOV R1, 10
PUSH R1, S1
MOV R1, 15
PUSH R1, S1
MOV R2, 0
POP R1, S1
ADD R2, R1
POP R1, S1
ADD R2, R1
POP R1, S1
ADD R2, R1
PRINT R2
HALT
""",
    },
}