# 🎓 Assembly Studio

סימולטור חינוכי ואינטראקטיבי ללימוד Assembly עם ממשק גרפי מתקדם.

## 🚀 הרצה מהירה

```bash
# הרצת התוכנית עם המבנה המודולרי החדש
python main.py

# או עם הקובץ המקורי (backup)
python battle_calc_runner.py
```

## 📦 מבנה הפרויקט המשופר

```
assembly-studio/
│
├── 🤖 vm/                      # Virtual Machine Core
│   ├── __init__.py            # Package exports
│   ├── machine.py             # Machine & AsmError classes
│   ├── parser.py              # Assembly parser
│   ├── executor.py            # Instruction executor (30+ opcodes)
│   └── translator.py          # Assembly→Python translator
│
├── 📚 data/                    # Data & Content
│   ├── __init__.py
│   └── examples.py            # 18 example programs (3 levels)
│
├── 🎨 gui/                     # Graphical Interface
│   ├── __init__.py
│   ├── styles.py              # Color schemes & styling
│   └── app.py                 # Main tkinter application
│
├── 🚀 main.py                  # Entry point
├── 📖 README.md                # This file
├── 📘 QUICKSTART.md            # Quick start guide
└── 💾 battle_calc_runner.py   # Original monolithic file (backup)
```

## ✨ תכונות

### מכונה וירטואלית מלאה
- **רגיסטרים**: R1, R2, R3 (כלליים), L1 (לולאות)
- **מחסניות**: S1, S2 עם מונים אוטומטיים C1, C2
- **זיכרון**: LIST - מערך של 33 תאים
- **דגלים**: ZERO, NEGATIVE
- **30+ פקודות**: MOV, ADD, SUB, MUL, DIV, MOD, INC, DEC, CLEAR, SWAP, PUSH, POP, RAND, PRINT, CMP, JZ, JNZ, GOTO, IF, LOOP, HALT

### ממשק משתמש מתקדם
- ✅ עורך קוד עם הדגשת תחביר
- ✅ ביצוע צעדי (step-by-step) עם הדגשת שורה נוכחית
- ✅ הרצה איטית עם עיכוב מתכוונן
- ✅ צעד אחורה (undo execution)
- ✅ תצוגה חזותית של רגיסטרים, מחסניות, זיכרון, ודגלים
- ✅ תרגום אוטומטי ל-Python
- ✅ 18 דוגמאות מובנות ב-3 רמות קושי
- ✅ מדריכים ועזרה בעברית

## 💡 דוגמאות שימוש

### שימוש פשוט ב-VM

```python
from vm import run_program

code = """
MOV R1, 10
ADD R1, 20
PRINT R1
HALT
"""

machine = run_program(code)
print(f"Output: {machine.output}")  # [30]
print(f"R1: {machine.regs['R1']}")  # 30
```

### ביצוע צעדי (Step-by-Step)

```python
from vm import run_program_steps

code = """
MOV R1, 5
MUL R1, 2
PRINT R1
HALT
"""

for machine, ip, line_no, raw, op, args in run_program_steps(code):
    print(f"Line {line_no}: {op} {' '.join(args)}")
    print(f"  R1 = {machine.regs['R1']}")
```

### תרגום ל-Python

```python
from vm import get_python_equivalent

python_code = get_python_equivalent('ADD', ['R1', '5'])
print(python_code)  # "R1 = R1 + 5"
```

## 🎯 יתרונות המבנה המודולרי

| תכונה | לפני | אחרי |
|-------|------|------|
| **מספר קבצים** | 1 קובץ | 12 קבצים |
| **שורות קוד** | 2,458 | ~1,900 (מאורגן יותר) |
| **ארגון** | מונוליתי | 3 packages נפרדים |
| **תחזוקה** | קשה | קלה |
| **בדיקות** | בלתי אפשרי | אפשרי לכל מודול |
| **שימוש חוזר** | לא | VM ללא GUI |

### יתרונות ספציפיים

1. **הפרדת אחריות** - כל מודול עם תפקיד ברור
2. **קלות תחזוקה** - קל למצוא ולתקן באגים
3. **הרחבה פשוטה** - קל להוסיף פקודות או תכונות
4. **בדיקות יחידה** - אפשר לבדוק כל מודול בנפרד
5. **שיתוף פעולה** - מספר מפתחים יכולים לעבוד במקביל
6. **שימוש חוזר** - VM כספרייה עצמאית

## 🧪 בדיקות

```bash
# בדיקה מהירה של כל המודולים
python3 -c "
from vm import Machine, run_program
from data import EXAMPLES

# Test VM
m = Machine()
assert m.regs['R1'] == 0

# Test execution
code = 'MOV R1, 10\nADD R1, 5\nPRINT R1\nHALT'
m = run_program(code)
assert m.output == [15]
print('✅ All tests passed!')
"
```

## 📚 תיעוד נוסף

- **QUICKSTART.md** - מדריך התחלה מהירה
- **vm/**: תיעוד מפורט של כל מודול
- **gui/**: הסבר על ממשק המשתמש

## 🔧 דרישות מערכת

- Python 3.7+
- tkinter (מגיע עם Python ברוב ההתקנות)
- אין תלויות חיצוניות נוספות

## 📜 רישיון

פרויקט חינוכי - שימוש חופשי

## 🎓 למי מיועד הפרויקט?

- סטודנטים ללימודי מדעי המחשב
- מורים להוראת Assembly
- כל מי שרוצה להבין תכנות ברמה נמוכה
- מפתחים שרוצים להבין איך מעבד עובד

## 🔄 מעבר מהקובץ המקורי

הקובץ המקורי `battle_calc_runner.py` נשאר במאגר כגיבוי.
כל הפונקציונליות זהה, רק מאורגנת יותר טוב!

```bash
# שתי הגרסאות עובדות זהה:
python battle_calc_runner.py  # גרסה מקורית
python main.py                 # גרסה מודולרית (מומלץ)
```

---

**נוצר עם ❤️ לקהילת המתכנתים הישראלית**
