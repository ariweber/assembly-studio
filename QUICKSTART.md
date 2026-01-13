# Quick Start Guide

## הרצת התוכנית

```bash
# עם המבנה החדש (מומלץ)
python main.py

# או עם הקובץ המקורי
python battle_calc_runner.py
```

## מבנה הפרויקט

```
├── vm/           # VM Core (מכונה וירטואלית)
├── data/         # Examples & Content  
├── gui/          # Graphical Interface
└── main.py       # Entry Point
```

## דוגמת שימוש פשוטה

```python
from vm import run_program

code = """
MOV R1, 10
ADD R1, 20
PRINT R1
HALT
"""

machine = run_program(code)
print(machine.output)  # [30]
```

הקוד המקורי נשאר ב-`battle_calc_runner.py` כגיבוי.
