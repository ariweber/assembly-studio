#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import random
import re
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from typing import Optional, List, Tuple, Dict, Any

# ============================================================
# VM + PARSER
# יעד-ואז-ערך (DST, SRC):
# MOV R1, 5 => R1 = 5
# ADD R1, 3 => R1 = R1 + 3
# ============================================================

TOKEN_SPLIT = re.compile(r"[,\s]+")

class AsmError(Exception):
    """שגיאה בזמן פרסור/הרצה עם שורת מקור"""
    def __init__(self, message: str, line_no: Optional[int] = None, raw_line: Optional[str] = None):
        super().__init__(message)
        self.line_no = line_no
        self.raw_line = raw_line

class Machine:
    """
    מכונה וירטואלית:
    - רגיסטרים: R1, R2, R3
    - מחסניות: S1, S2
    - מונים: C1, C2 (= גדלי המחסניות)
    - רגיסטר לולאות: L1
    - זיכרון: LIST (33 תאים, אינדקס 0..32) מאותחל 0..32
    - דגלים: ZERO, NEGATIVE
    - פלט: output (רשימת ערכים שהודפסו)
    """
    def __init__(self):
        self.regs = {"R1": 0, "R2": 0, "R3": 0}
        self.stacks = {"S1": [], "S2": []}
        self.L1 = 0
        self.LIST = list(range(33))
        self.output: List[int] = []
        self.flags = {"ZERO": False, "NEGATIVE": False}
        self.execution_history: List[Dict[str, Any]] = []

    def get_counter(self, name: str) -> int:
        if name == "C1":
            return len(self.stacks["S1"])
        if name == "C2":
            return len(self.stacks["S2"])
        raise AsmError(f"מונה לא ידוע: {name}")

    def update_flags(self, value: int):
        self.flags["ZERO"] = (value == 0)
        self.flags["NEGATIVE"] = (value < 0)

    def get_value(self, token: str) -> int:
        token = token.strip()
        if token in self.regs:
            return int(self.regs[token])
        if token in ("C1", "C2"):
            return int(self.get_counter(token))
        if token == "L1":
            return int(self.L1)
        if re.fullmatch(r"-?\d+", token):
            return int(token)
        raise AsmError(f"ערך לא חוקי: {token}")

    def _parse_list_expr(self, expr: str) -> Tuple[str, int]:
        """
        תומך ב: [LIST+R1], [LIST+R2], [LIST+R3], [LIST+L1], [LIST+5]
        """
        expr = expr.strip()
        m = re.fullmatch(r"\[LIST\s*\+\s*([A-Za-z0-9\-]+)\s*\]", expr)
        if not m:
            raise AsmError(f"ביטוי LIST שגוי: {expr}")
        inside = m.group(1)
        if inside in ("R1", "R2", "R3"):
            idx = int(self.regs[inside])
            return inside, idx
        if inside == "L1":
            idx = int(self.L1)
            return inside, idx
        if re.fullmatch(r"-?\d+", inside):
            idx = int(inside)
            return inside, idx
        raise AsmError(f"אינדקס LIST לא חוקי: {inside}")

    def read_list(self, expr: str) -> int:
        src, idx = self._parse_list_expr(expr)
        if not (0 <= idx < len(self.LIST)):
            raise AsmError(f"אינדקס LIST מחוץ לטווח: {idx} (מ-{src})")
        return int(self.LIST[idx])

    def write_list(self, expr: str, value: int):
        src, idx = self._parse_list_expr(expr)
        if not (0 <= idx < len(self.LIST)):
            raise AsmError(f"אינדקס LIST מחוץ לטווח: {idx} (מ-{src})")
        self.LIST[idx] = int(value)

    def set_target(self, target: str, value: int):
        target = target.strip()
        if target in self.regs:
            self.regs[target] = int(value)
            self.update_flags(int(value))
            return
        if target == "L1":
            self.L1 = int(value)
            return
        if target.strip().startswith("[LIST"):
            self.write_list(target, value)
            return
        raise AsmError(f"יעד לא ידוע: {target}")

    def save_state(self, step_info: str):
        self.execution_history.append({
            "step": step_info,
            "R1": self.regs["R1"],
            "R2": self.regs["R2"],
            "R3": self.regs["R3"],
            "L1": self.L1,
            "C1": len(self.stacks["S1"]),
            "C2": len(self.stacks["S2"]),
            "S1": self.stacks["S1"].copy(),
            "S2": self.stacks["S2"].copy(),
            "ZERO": self.flags["ZERO"],
            "NEGATIVE": self.flags["NEGATIVE"],
        })

def parse_program(text: str) -> Tuple[List[Tuple[str, List[str], str, int]], Dict[str, int]]:
    """
    תומך:
    - הערות: ; או #
    - תוויות: LABEL:
    - מפריד פסיקים/רווחים
    """
    instructions: List[Tuple[str, List[str], str, int]] = []
    labels: Dict[str, int] = {}
    lines = text.splitlines()
    for line_no, raw in enumerate(lines, start=1):
        line = raw.split(";", 1)[0].split("#", 1)[0].strip()
        if not line:
            continue
        # label
        if line.endswith(":"):
            label = line[:-1].strip()
            if not label:
                raise AsmError("תווית ריקה", line_no=line_no, raw_line=raw)
            key = label.upper()
            if key in labels:
                raise AsmError(f"תווית כפולה '{label}'", line_no=line_no, raw_line=raw)
            labels[key] = len(instructions)
            continue
        parts = [p for p in TOKEN_SPLIT.split(line) if p]
        if not parts:
            continue
        op = parts[0].upper()
        args = parts[1:]
        instructions.append((op, args, raw, line_no))
    return instructions, labels

def eval_condition(m: Machine, left: str, op: str, right: str) -> bool:
    lv = m.get_value(left)
    rv = m.get_value(right)
    if op == "==":
        return lv == rv
    if op == "!=":
        return lv != rv
    if op == ">":
        return lv > rv
    if op == "<":
        return lv < rv
    if op == ">=":
        return lv >= rv
    if op == "<=":
        return lv <= rv
    raise AsmError(f"אופרטור לא נתמך: {op}")

def run_program(program_text: str, seed: Optional[int] = None, max_steps: int = 200000, save_history: bool = False) -> Machine:
    """
    הרצת תוכנית עד הסוף.
    משתמש ב-run_program_steps() לשמירת התנהגות זהה.
    """
    m = None
    for m, ip, line_no, raw, op, args in run_program_steps(program_text, seed, max_steps, save_history):
        pass
    return m

def run_program_steps(program_text: str, seed: Optional[int] = None, max_steps: int = 200000, save_history: bool = False):
    """
    Generator שמחזיר (machine, ip, line_no, raw_line, op, args) אחרי כל הוראה.
    """
    if seed is not None:
        random.seed(seed)

    m = Machine()
    ins, labels = parse_program(program_text)
    ip = 0
    steps = 0

    def err(msg: str, line_no: int, raw: str):
        raise AsmError(msg, line_no=line_no, raw_line=raw)

    while 0 <= ip < len(ins):
        if steps >= max_steps:
            raise AsmError("חריגה ממקסימום צעדים (כנראה לולאה אינסופית).")
        steps += 1

        op, args, raw, line_no = ins[ip]

        if save_history:
            m.save_state(f"{line_no}: {op} {' '.join(args)}")

        try:
            if op == "HALT":
                yield (m, ip, line_no, raw, op, args)
                break
            elif op == "NOP":
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "MOV":
                if len(args) != 2:
                    err("MOV דורש 2 ארגומנטים: MOV יעד, מקור", line_no, raw)
                dst, src = args[0], args[1]
                if src.strip().startswith("[LIST"):
                    val = m.read_list(src)
                else:
                    val = m.get_value(src)
                m.set_target(dst, val)
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "ADD":
                if len(args) != 2:
                    err("ADD דורש 2 ארגומנטים: ADD יעד, מקור", line_no, raw)
                dst, src = args[0], args[1]
                if dst not in m.regs:
                    err("ADD: היעד חייב להיות רגיסטר (R1/R2/R3)", line_no, raw)
                v = m.get_value(src)
                m.regs[dst] = int(m.regs[dst]) + int(v)
                m.update_flags(m.regs[dst])
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "SUB":
                if len(args) != 2:
                    err("SUB דורש 2 ארגומנטים: SUB יעד, מקור", line_no, raw)
                dst, src = args[0], args[1]
                if dst not in m.regs:
                    err("SUB: היעד חייב להיות רגיסטר (R1/R2/R3)", line_no, raw)
                v = m.get_value(src)
                m.regs[dst] = int(m.regs[dst]) - int(v)
                m.update_flags(m.regs[dst])
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "MUL":
                if len(args) != 2:
                    err("MUL דורש 2 ארגומנטים: MUL יעד, מקור", line_no, raw)
                dst, src = args[0], args[1]
                if dst not in m.regs:
                    err("MUL: היעד חייב להיות רגיסטר", line_no, raw)
                v = m.get_value(src)
                m.regs[dst] = int(m.regs[dst]) * int(v)
                m.update_flags(m.regs[dst])
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "DIV":
                if len(args) != 2:
                    err("DIV דורש 2 ארגומנטים: DIV יעד, מקור", line_no, raw)
                dst, src = args[0], args[1]
                if dst not in m.regs:
                    err("DIV: היעד חייב להיות רגיסטר", line_no, raw)
                v = m.get_value(src)
                if v == 0:
                    err("חילוק באפס!", line_no, raw)
                m.regs[dst] = int(m.regs[dst]) // int(v)
                m.update_flags(m.regs[dst])
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "MOD":
                if len(args) != 2:
                    err("MOD דורש 2 ארגומנטים: MOD יעד, מקור", line_no, raw)
                dst, src = args[0], args[1]
                if dst not in m.regs:
                    err("MOD: היעד חייב להיות רגיסטר", line_no, raw)
                v = m.get_value(src)
                if v == 0:
                    err("מודולו באפס!", line_no, raw)
                m.regs[dst] = int(m.regs[dst]) % int(v)
                m.update_flags(m.regs[dst])
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "INC":
                if len(args) != 1:
                    err("INC דורש ארגומנט אחד: INC R", line_no, raw)
                r = args[0]
                if r not in m.regs:
                    err("INC: חייב להיות רגיסטר", line_no, raw)
                m.regs[r] += 1
                m.update_flags(m.regs[r])
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "DEC":
                if len(args) != 1:
                    err("DEC דורש ארגומנט אחד: DEC R", line_no, raw)
                r = args[0]
                if r not in m.regs:
                    err("DEC: חייב להיות רגיסטר", line_no, raw)
                m.regs[r] -= 1
                m.update_flags(m.regs[r])
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "CLEAR":
                if len(args) != 1:
                    err("CLEAR דורש ארגומנט אחד: CLEAR R", line_no, raw)
                r = args[0]
                if r not in m.regs:
                    err("CLEAR: חייב להיות רגיסטר", line_no, raw)
                m.regs[r] = 0
                m.update_flags(0)
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "SWAP":
                if len(args) != 2:
                    err("SWAP דורש 2 ארגומנטים: SWAP R1, R2", line_no, raw)
                a, b = args[0], args[1]
                if a not in m.regs or b not in m.regs:
                    err("SWAP: שני הארגומנטים חייבים להיות רגיסטרים", line_no, raw)
                m.regs[a], m.regs[b] = m.regs[b], m.regs[a]
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "PUSH":
                if len(args) != 2:
                    err("PUSH דורש 2 ארגומנטים: PUSH R, S1|S2", line_no, raw)
                r, s = args[0], args[1].upper()
                if r not in m.regs:
                    err("PUSH: ארגומנט ראשון חייב להיות רגיסטר", line_no, raw)
                if s not in m.stacks:
                    err("PUSH: מחסנית חייבת להיות S1 או S2", line_no, raw)
                m.stacks[s].append(int(m.regs[r]))
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "POP":
                if len(args) != 2:
                    err("POP דורש 2 ארגומנטים: POP R, S1|S2", line_no, raw)
                r, s = args[0], args[1].upper()
                if r not in m.regs:
                    err("POP: ארגומנט ראשון חייב להיות רגיסטר", line_no, raw)
                if s not in m.stacks:
                    err("POP: מחסנית חייבת להיות S1 או S2", line_no, raw)
                if not m.stacks[s]:
                    err(f"POP ממחסנית ריקה {s}", line_no, raw)
                m.regs[r] = int(m.stacks[s].pop())
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "RAND":
                if len(args) != 1:
                    err("RAND דורש ארגומנט אחד: RAND R", line_no, raw)
                r = args[0]
                if r not in m.regs:
                    err("RAND: חייב להיות רגיסטר", line_no, raw)
                m.regs[r] = random.randint(0, 32)
                m.update_flags(m.regs[r])
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "PRINT":
                if len(args) != 1:
                    err("PRINT דורש ארגומנט אחד: PRINT X", line_no, raw)
                v = m.get_value(args[0])
                m.output.append(int(v))
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "CMP":
                if len(args) != 2:
                    err("CMP דורש 2 ארגומנטים: CMP A, B", line_no, raw)
                a = m.get_value(args[0])
                b = m.get_value(args[1])
                diff = int(a) - int(b)
                m.update_flags(diff)
                yield (m, ip, line_no, raw, op, args)
                ip += 1
            elif op == "JZ":
                if len(args) != 1:
                    err("JZ דורש ארגומנט אחד: JZ LABEL", line_no, raw)
                lbl = args[0].upper()
                if lbl not in labels:
                    err(f"תווית לא ידועה '{args[0]}'", line_no, raw)
                yield (m, ip, line_no, raw, op, args)
                if m.flags["ZERO"]:
                    ip = labels[lbl]
                else:
                    ip += 1
            elif op == "JNZ":
                if len(args) != 1:
                    err("JNZ דורש ארגומנט אחד: JNZ LABEL", line_no, raw)
                lbl = args[0].upper()
                if lbl not in labels:
                    err(f"תווית לא ידועה '{args[0]}'", line_no, raw)
                yield (m, ip, line_no, raw, op, args)
                if not m.flags["ZERO"]:
                    ip = labels[lbl]
                else:
                    ip += 1
            elif op == "GOTO":
                if len(args) != 1:
                    err("GOTO דורש ארגומנט אחד: GOTO LABEL", line_no, raw)
                lbl = args[0].upper()
                if lbl not in labels:
                    err(f"תווית לא ידועה '{args[0]}'", line_no, raw)
                yield (m, ip, line_no, raw, op, args)
                ip = labels[lbl]
            elif op == "IF":
                if len(args) != 5 or args[3].upper() != "GOTO":
                    err("תחביר IF שגוי: IF A == B GOTO LABEL", line_no, raw)
                left, cond_op, right, _, label = args
                lbl = label.upper()
                if lbl not in labels:
                    err(f"תווית לא ידועה '{label}'", line_no, raw)
                yield (m, ip, line_no, raw, op, args)
                if eval_condition(m, left, cond_op, right):
                    ip = labels[lbl]
                else:
                    ip += 1
            elif op == "LOOP":
                if len(args) != 1:
                    err("LOOP דורש ארגומנט אחד: LOOP LABEL", line_no, raw)
                lbl = args[0].upper()
                if lbl not in labels:
                    err(f"תווית לא ידועה '{args[0]}'", line_no, raw)
                m.L1 -= 1
                yield (m, ip, line_no, raw, op, args)
                if m.L1 != 0:
                    ip = labels[lbl]
                else:
                    ip += 1
            else:
                err(f"הוראה לא ידועה '{op}'", line_no, raw)

        except AsmError as e:
            if e.line_no is None:
                e.line_no = line_no
                e.raw_line = raw
            raise e

def get_python_equivalent(op: str, args: List[str]) -> str:
    """
    מחזיר קוד Python מקביל לפקודת Assembly.
    """
    op = op.upper()
    
    if op == "MOV":
        if len(args) == 2:
            dst, src = args[0], args[1]
            # טיפול ב-LIST
            if src.strip().startswith("[LIST"):
                # [LIST+R1] או [LIST+5]
                expr = src.strip()[6:-1]  # הסר [LIST ו-]
                if "+" in expr:
                    idx_part = expr.split("+")[1].strip()
                    return f"{dst} = LIST[{idx_part}]"
                return f"{dst} = LIST[{expr}]"
            elif dst.strip().startswith("[LIST"):
                # [LIST+R1] = value
                expr = dst.strip()[6:-1]  # הסר [LIST ו-]
                if "+" in expr:
                    idx_part = expr.split("+")[1].strip()
                    return f"LIST[{idx_part}] = {src}"
                return f"LIST[{expr}] = {src}"
            else:
                return f"{dst} = {src}"
    
    elif op == "ADD":
        if len(args) == 2:
            dst, src = args[0], args[1]
            return f"{dst} = {dst} + {src}"
    
    elif op == "SUB":
        if len(args) == 2:
            dst, src = args[0], args[1]
            return f"{dst} = {dst} - {src}"
    
    elif op == "MUL":
        if len(args) == 2:
            dst, src = args[0], args[1]
            return f"{dst} = {dst} * {src}"
    
    elif op == "DIV":
        if len(args) == 2:
            dst, src = args[0], args[1]
            return f"{dst} = {dst} // {src}"
    
    elif op == "MOD":
        if len(args) == 2:
            dst, src = args[0], args[1]
            return f"{dst} = {dst} % {src}"
    
    elif op == "INC":
        if len(args) == 1:
            r = args[0]
            return f"{r} = {r} + 1"
    
    elif op == "DEC":
        if len(args) == 1:
            r = args[0]
            return f"{r} = {r} - 1"
    
    elif op == "CLEAR":
        if len(args) == 1:
            r = args[0]
            return f"{r} = 0"
    
    elif op == "SWAP":
        if len(args) == 2:
            a, b = args[0], args[1]
            return f"{a}, {b} = {b}, {a}"
    
    elif op == "PUSH":
        if len(args) == 2:
            r, s = args[0], args[1].upper()
            return f"{s}.append({r})"
    
    elif op == "POP":
        if len(args) == 2:
            r, s = args[0], args[1].upper()
            return f"{r} = {s}.pop()"
    
    elif op == "RAND":
        if len(args) == 1:
            r = args[0]
            return f"{r} = random.randint(0, 32)"
    
    elif op == "PRINT":
        if len(args) == 1:
            return f"print({args[0]})"
    
    elif op == "HALT":
        return "exit()"
    
    elif op == "IF":
        if len(args) == 5 and args[3].upper() == "GOTO":
            left, cond_op, right, _, label = args
            return f"if {left} {cond_op} {right}: goto {label}"
    
    elif op == "LOOP":
        if len(args) == 1:
            label = args[0]
            return f"L1 -= 1; if L1 != 0: goto {label}"
    
    elif op == "GOTO":
        if len(args) == 1:
            return f"goto {args[0]}"
    
    elif op == "JZ":
        if len(args) == 1:
            return f"if ZERO: goto {args[0]}"
    
    elif op == "JNZ":
        if len(args) == 1:
            return f"if not ZERO: goto {args[0]}"
    
    elif op == "CMP":
        if len(args) == 2:
            a, b = args[0], args[1]
            return f"ZERO, NEGATIVE = ({a} - {b} == 0), ({a} - {b} < 0)"
    
    elif op == "NOP":
        return "pass"
    
    # אם לא מצאנו תרגום, נחזיר משהו כללי
    return f"# {op} {' '.join(args)}"

# ============================================================
# EXAMPLES (DST, SRC + פסיקים)
# ============================================================

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

# ============================================================
# GUI עם צבעוניות
# ============================================================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Assembly Studio — תרגול Assembly")
        self.geometry("1400x900")
        self.option_add('*tearOff', False)

        # Color scheme
        self.colors = {
            'bg': '#f5f5f5',
            'card_bg': '#ffffff',
            'primary': '#2196F3',
            'success': '#4CAF50',
            'warning': '#FF9800',
            'error': '#F44336',
            'text': '#212121',
            'text_secondary': '#757575',
            'accent': '#00BCD4',
            'register': '#E3F2FD',
            'stack': '#FFF3E0',
            'memory': '#F3E5F5',
            'flag_on': '#4CAF50',
            'flag_off': '#9E9E9E',
        }
        
        self.configure(bg=self.colors['bg'])

        # Stepping state
        self.stepper = None
        self.step_machine = None
        self.slow_running = False
        self.after_id = None
        self.step_history = []  # היסטוריה של מצבים (machine, ip, line_no, raw, op, args)
        self.step_history_index = -1  # אינדקס נוכחי בהיסטוריה

        # Current example navigation
        self.current_level = None
        self.current_example = None

        self._build_header_bar()
        self._build_main()

        # Load first example from level 1
        first_level = list(EXAMPLES.keys())[0]
        first_example = list(EXAMPLES[first_level].keys())[0]
        self.load_example(first_level, first_example)
        self.update_line_numbers()
        self.bind("<F5>", lambda e: self.on_run())

    def _build_header_bar(self):
        """Build custom header bar aligned to the right (RTL)"""
        header_bar = tk.Frame(self, bg=self.colors['card_bg'], relief=tk.RAISED, bd=1, height=35)
        header_bar.pack(fill="x", padx=0, pady=0)
        header_bar.pack_propagate(False)
        
        inner = tk.Frame(header_bar, bg=self.colors['card_bg'])
        inner.pack(fill="both", expand=True, padx=10, pady=5)
        
        # עזרה (rightmost) - using Button with postcommand menu
        help_btn = tk.Button(inner, text="עזרה",
                            bg=self.colors['card_bg'], fg=self.colors['text'],
                            font=("Arial", 10), relief=tk.FLAT, padx=10, pady=5,
                            cursor="hand2", anchor="e")
        help_btn.pack(side="right", padx=5)
        
        help_menu = tk.Menu(help_btn, tearoff=0)
        help_menu.add_command(label="📘 מדריך למתחיל", command=self.show_beginner_guide)
        help_menu.add_command(label="🧾 שיעור ראשון (עם קוד)", command=self.show_first_lesson)
        help_menu.add_command(label="❓ שאלות נפוצות", command=self.show_faq)
        help_menu.add_separator()
        help_menu.add_command(label="מדריך קצר", command=self.show_quick_guide)
        
        def show_help_menu(e):
            try:
                x = help_btn.winfo_rootx()
                y = help_btn.winfo_rooty() + help_btn.winfo_height()
                help_menu.post(x, y)
            except:
                help_menu.post(e.x_root, e.y_root)
        help_btn.bind("<Button-1>", show_help_menu)
        
        # דוגמאות
        ex_btn = tk.Button(inner, text="דוגמאות",
                          bg=self.colors['card_bg'], fg=self.colors['text'],
                          font=("Arial", 10), relief=tk.FLAT, padx=10, pady=5,
                          cursor="hand2", anchor="e")
        ex_btn.pack(side="right", padx=5)
        
        ex_menu = tk.Menu(ex_btn, tearoff=0)
        for level_name, examples_dict in EXAMPLES.items():
            level_menu = tk.Menu(ex_menu, tearoff=0)
            ex_menu.add_cascade(label=level_name, menu=level_menu)
            for ex_name in examples_dict.keys():
                level_menu.add_command(
                    label=ex_name,
                    command=lambda l=level_name, e=ex_name: self.load_example(l, e)
                )
        
        def show_ex_menu(e):
            try:
                x = ex_btn.winfo_rootx()
                y = ex_btn.winfo_rooty() + ex_btn.winfo_height()
                ex_menu.post(x, y)
            except:
                ex_menu.post(e.x_root, e.y_root)
        ex_btn.bind("<Button-1>", show_ex_menu)
        
        # קובץ (leftmost in RTL visual order)
        file_btn = tk.Button(inner, text="קובץ",
                            bg=self.colors['card_bg'], fg=self.colors['text'],
                            font=("Arial", 10), relief=tk.FLAT, padx=10, pady=5,
                            cursor="hand2", anchor="e")
        file_btn.pack(side="right", padx=5)
        
        file_menu = tk.Menu(file_btn, tearoff=0)
        file_menu.add_command(label="חדש", command=self.new_file)
        file_menu.add_command(label="פתח...", command=self.open_file)
        file_menu.add_command(label="שמור...", command=self.save_file)
        file_menu.add_separator()
        file_menu.add_command(label="יציאה", command=self.quit)
        
        def show_file_menu(e):
            try:
                x = file_btn.winfo_rootx()
                y = file_btn.winfo_rooty() + file_btn.winfo_height()
                file_menu.post(x, y)
            except:
                file_menu.post(e.x_root, e.y_root)
        file_btn.bind("<Button-1>", show_file_menu)
        
        # Hover effects for buttons
        for btn in [help_btn, ex_btn, file_btn]:
            def make_hover(b):
                def on_enter(e):
                    b.config(bg="#e0e0e0")
                def on_leave(e):
                    b.config(bg=self.colors['card_bg'])
                b.bind("<Enter>", on_enter)
                b.bind("<Leave>", on_leave)
            make_hover(btn)
        
        # Keep keyboard shortcuts
        self.bind("<Control-n>", lambda e: self.new_file())
        self.bind("<Control-s>", lambda e: self.save_file())

    def _build_controls_row(self, parent: tk.Frame) -> None:
        """Build horizontal controls row at top of right panel"""
        inner = tk.Frame(parent, bg=self.colors['card_bg'])
        inner.pack(fill="x", padx=8, pady=8)
        
        # Group controls from right to left (RTL feel)
        # Fields on the right
        fields_frame = tk.Frame(inner, bg=self.colors['card_bg'])
        fields_frame.pack(side="right", padx=5)
        
        # Seed entry (RTL: label on right, entry on left)
        seed_frame = tk.Frame(fields_frame, bg=self.colors['card_bg'])
        seed_frame.pack(side="right", padx=5)
        tk.Label(seed_frame, text="Seed:", bg=self.colors['card_bg'], fg=self.colors['text'], 
                font=("Arial", 9)).pack(side="right", padx=(5, 0))
        self.seed_var = tk.StringVar(value="")
        seed_entry = tk.Entry(seed_frame, textvariable=self.seed_var, width=10, font=("Arial", 9))
        seed_entry.pack(side="left")
        
        # Max steps entry
        steps_frame = tk.Frame(fields_frame, bg=self.colors['card_bg'])
        steps_frame.pack(side="right", padx=5)
        tk.Label(steps_frame, text="Max steps:", bg=self.colors['card_bg'], fg=self.colors['text'],
                font=("Arial", 9)).pack(side="right", padx=(5, 0))
        self.steps_var = tk.StringVar(value="200000")
        steps_entry = tk.Entry(steps_frame, textvariable=self.steps_var, width=10, font=("Arial", 9))
        steps_entry.pack(side="left")
        
        # Delay entry
        delay_frame = tk.Frame(fields_frame, bg=self.colors['card_bg'])
        delay_frame.pack(side="right", padx=5)
        tk.Label(delay_frame, text="עיכוב (ms):", bg=self.colors['card_bg'], fg=self.colors['text'],
                font=("Arial", 9), justify="right", anchor="e").pack(side="right", padx=(5, 0))
        self.delay_var = tk.StringVar(value="150")
        delay_entry = tk.Entry(delay_frame, textvariable=self.delay_var, width=8, font=("Arial", 9))
        delay_entry.pack(side="left")
        
        # History checkbox
        self.history_var = tk.BooleanVar(value=False)
        history_check = tk.Checkbutton(fields_frame, text="שמור היסטוריה", variable=self.history_var, 
                      bg=self.colors['card_bg'], fg=self.colors['text'], 
                      selectcolor=self.colors['card_bg'], font=("Arial", 9))
        history_check.pack(side="right", padx=5)
        
        # Separator
        ttk.Separator(inner, orient=tk.VERTICAL).pack(side="right", fill="y", padx=8)
        
        # Buttons grouped on the left (RTL: buttons on left, fields on right)
        buttons_frame = tk.Frame(inner, bg=self.colors['card_bg'])
        buttons_frame.pack(side="right", padx=5)
        
        # Output buttons
        self._create_toolbar_button(buttons_frame, "📋 העתק פלט", self.copy_output, self.colors['text_secondary'])
        self._create_toolbar_button(buttons_frame, "🗑 נקה פלט", self.clear_output, self.colors['text_secondary'])
        
        ttk.Separator(buttons_frame, orient=tk.VERTICAL).pack(side="right", fill="y", padx=8)
        
        # Main action buttons
        self._create_toolbar_button(buttons_frame, "⏹ איפוס", self.on_reset, self.colors['warning'])
        self.slow_run_btn = self._create_toolbar_button(buttons_frame, "⏯ הרצה איטית", 
                                                         self.on_slow_run, self.colors['accent'])
        self._create_toolbar_button(buttons_frame, "⏭ צעד", self.on_step, self.colors['primary'])
        self._create_toolbar_button(buttons_frame, "▶ הרץ (F5)", self.on_run, self.colors['success'])
        
        # Navigation buttons for examples (kept for existing features)
        ttk.Separator(inner, orient=tk.VERTICAL).pack(side="right", fill="y", padx=8)
        
        nav_frame = tk.Frame(inner, bg=self.colors['card_bg'])
        nav_frame.pack(side="right", padx=5)
        
        tk.Label(nav_frame, text="תרגילים:", bg=self.colors['card_bg'], 
                fg=self.colors['text'], font=("Arial", 9), justify="right", anchor="e").pack(side="right", padx=5)
        self.next_example_btn = self._create_toolbar_button(nav_frame, "הבא ▶", 
                                                             self.next_example, self.colors['text_secondary'])
        self.prev_example_btn = self._create_toolbar_button(nav_frame, "◀ קודם", 
                                                             self.prev_example, self.colors['text_secondary'])
        
        # Step back button (kept for existing features)
        ttk.Separator(inner, orient=tk.VERTICAL).pack(side="right", fill="y", padx=8)
        self._create_toolbar_button(inner, "◀ צעד קודם", self.on_step_back, self.colors['text_secondary'])

    def _create_toolbar_button(self, parent, text, command, color):
        btn = tk.Button(parent, text=text, command=command, 
                       bg=color, fg='white', font=("Arial", 9, "bold"),
                       relief=tk.RAISED, bd=1, padx=10, pady=5,
                       cursor="hand2", activebackground=color)
        btn.pack(side="left", padx=3)
        
        # Hover effect
        def on_enter(e):
            btn['bg'] = self._darken_color(color)
        def on_leave(e):
            btn['bg'] = color
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
    
    def _create_toolbar_button_vertical(self, parent, text, command, color):
        """Create a button for vertical toolbar"""
        btn = tk.Button(parent, text=text, command=command, 
                       bg=color, fg='white', font=("Arial", 9, "bold"),
                       relief=tk.RAISED, bd=1, padx=10, pady=5,
                       cursor="hand2", activebackground=color)
        btn.pack(fill="x", pady=3)
        
        # Hover effect
        def on_enter(e):
            btn['bg'] = self._darken_color(color)
        def on_leave(e):
            btn['bg'] = color
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn

    def _darken_color(self, color):
        """Make color slightly darker for hover effect"""
        # Simple darkening by reducing each RGB component
        if color.startswith('#'):
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            r, g, b = max(0, r-30), max(0, g-30), max(0, b-30)
            return f'#{r:02x}{g:02x}{b:02x}'
        return color

    def _build_main(self):
        # Main container with two columns using Frame (not PanedWindow)
        main = tk.Frame(self, bg=self.colors['bg'])
        main.pack(fill="both", expand=True, padx=10, pady=8)
        
        # LEFT PANEL - Code Editor (must be visible!)
        left_frame = tk.Frame(main, bg=self.colors['bg'])
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Header for code editor (RTL: text on right)
        header = tk.Frame(left_frame, bg=self.colors['bg'])
        header.pack(fill="x", pady=(0, 5))
        tk.Label(header, text="קוד 📝", font=("Arial", 12, "bold"), 
                bg=self.colors['bg'], fg=self.colors['text'],
                anchor="e", justify="right").pack(side="right")
        
        # Code editor frame
        code_frame = tk.Frame(left_frame, bg=self.colors['card_bg'], 
                             relief=tk.SOLID, bd=1)
        code_frame.pack(fill="both", expand=True)
        
        # Line numbers (RIGHT side for RTL)
        self.line_numbers = tk.Text(code_frame, width=4, padx=3, takefocus=0, 
                                    border=0, background="#e9e9e9", 
                                    fg=self.colors['text_secondary'],
                                    state="disabled", wrap="none", 
                                    font=("Courier New", 10))
        self.line_numbers.pack(side="right", fill="y")
        
        # Scrollbar (LEFT side for RTL)
        scroll = ttk.Scrollbar(code_frame, command=self._on_scrollbar)
        scroll.pack(side="left", fill="y")
        
        # Code text widget (CENTER)
        self.code = tk.Text(code_frame, wrap="none", undo=True, 
                           font=("Courier New", 10),
                           bg=self.colors['card_bg'], fg=self.colors['text'],
                           insertbackground=self.colors['primary'],
                           yscrollcommand=scroll.set)
        self.code.pack(side="left", fill="both", expand=True)

        # Syntax highlighting colors
        self.code.tag_configure("errorline", background="#ffebee")
        self.code.tag_configure("currentline", background="#e3f2fd")
        self.code.tag_configure("comment", foreground="#757575", font=("Courier New", 10, "italic"))
        self.code.tag_configure("keyword", foreground="#1976D2", font=("Courier New", 10, "bold"))
        self.code.tag_configure("register", foreground="#D32F2F", font=("Courier New", 10, "bold"))
        self.code.tag_configure("number", foreground="#388E3C")

        self.code.bind("<KeyRelease>", self.update_line_numbers)
        self.code.bind("<Button-4>", self.update_line_numbers)
        self.code.bind("<Button-5>", self.update_line_numbers)

        # RIGHT PANEL - Cards and outputs
        right_frame = tk.Frame(main, bg=self.colors['bg'], width=400)
        right_frame.pack(side="right", fill="both", expand=False, padx=(5, 0))
        right_frame.pack_propagate(False)
        
        # Controls at top
        controls_frame = tk.Frame(right_frame, bg=self.colors['card_bg'], 
                                 relief=tk.RAISED, bd=1)
        controls_frame.pack(fill="x", pady=(0, 5))
        self._build_controls_row(controls_frame)

        # Cards container with scrolling
        cards_frame = tk.Frame(right_frame, bg=self.colors['bg'])
        cards_frame.pack(fill="both", expand=True)

        cards_scroll = ttk.Scrollbar(cards_frame, orient=tk.VERTICAL)
        cards_canvas = tk.Canvas(cards_frame, yscrollcommand=cards_scroll.set, 
                                bg=self.colors['bg'], highlightthickness=0)
        cards_scroll.config(command=cards_canvas.yview)
        cards_scroll.pack(side="right", fill="y")
        cards_canvas.pack(side="left", fill="both", expand=True)

        cards_container = tk.Frame(cards_canvas, bg=self.colors['bg'])
        cards_canvas.create_window((0, 0), window=cards_container, anchor="nw")

        def update_cards_scroll(event):
            cards_canvas.configure(scrollregion=cards_canvas.bbox("all"))
        cards_container.bind("<Configure>", update_cards_scroll)

        # Task card
        task_card = self._create_card(cards_container, "📋 משימה")
        self.task_label = tk.Label(task_card, text="(אין משימה בקוד הנוכחי)", 
                                   wraplength=300, justify="right",
                                   bg=self.colors['card_bg'], fg=self.colors['text'],
                                   font=("Arial", 10))
        self.task_label.pack(anchor="e", padx=5, pady=5)

        # Python equivalent card
        python_card = self._create_card(cards_container, "🐍 קוד Python מקביל", "#E8F5E9")
        self.python_text = scrolledtext.ScrolledText(python_card, height=4,
                                                     font=("Courier New", 9),
                                                     state="disabled", bg="white",
                                                     fg="#2E7D32", wrap="word")
        self.python_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.python_text.config(state="normal")
        self.python_text.insert("1.0", "# הקוד Python יופיע כאן כשתריץ צעד")
        self.python_text.config(state="disabled")

        # Registers card (RTL: value on left, label on right)
        regs_card = self._create_card(cards_container, "🔢 רגיסטרים", self.colors['register'])
        regs_grid = tk.Frame(regs_card, bg=self.colors['register'])
        regs_grid.pack(fill="x", padx=5, pady=5)

        self.reg_labels = {}
        for i, reg in enumerate(["R1", "R2", "R3", "L1"]):
            row, col = i // 2, i % 2
            # Value on LEFT (RTL)
            lbl = tk.Label(regs_grid, text="0", 
                          font=("Courier New", 13, "bold"),
                          width=8, anchor="e",  # Right-aligned text
                          bg=self.colors['register'],
                          fg=self.colors['primary'])
            lbl.grid(row=row, column=col*2, sticky="e", padx=5, pady=4)
            # Label on RIGHT (RTL)
            tk.Label(regs_grid, text=f":{reg}",  # Colon on right
                    font=("Arial", 10, "bold"),
                    bg=self.colors['register'], 
                    fg=self.colors['text']).grid(
                        row=row, column=col*2+1, sticky="w", padx=5, pady=4)
            self.reg_labels[reg] = lbl

        # Flags card
        flags_card = self._create_card(cards_container, "🚩 דגלים", "#FFF9C4")
        flags_grid = tk.Frame(flags_card, bg="#FFF9C4")
        flags_grid.pack(fill="x", padx=5, pady=5)

        self.flag_labels = {}
        for i, flag in enumerate(["ZERO", "NEGATIVE"]):
            tk.Label(flags_grid, text=f"{flag}:", font=("Arial", 10, "bold"),
                    bg="#FFF9C4", fg=self.colors['text']).grid(
                        row=0, column=i*2, sticky="e", padx=5, pady=4)
            lbl = tk.Label(flags_grid, text="לא", font=("Arial", 11, "bold"),
                          width=5, bg="#FFF9C4", fg=self.colors['flag_off'])
            lbl.grid(row=0, column=i*2+1, sticky="w", padx=5, pady=4)
            self.flag_labels[flag] = lbl

        # Stacks card (RTL: S1 on right, S2 on left)
        stacks_card = self._create_card(cards_container, "📚 מחסניות", self.colors['stack'])
        
        stacks_frame = tk.Frame(stacks_card, bg=self.colors['stack'])
        stacks_frame.pack(fill="x", padx=5, pady=5)

        # S1 on RIGHT (RTL)
        s1_frame = tk.Frame(stacks_frame, bg=self.colors['stack'])
        s1_frame.pack(side="right", padx=5, expand=True, fill="both")
        tk.Label(s1_frame, text="S1", font=("Arial", 10, "bold"),
                bg=self.colors['stack'], fg=self.colors['text']).pack()
        self.stack1_listbox = tk.Listbox(s1_frame, height=4, width=12,
                                         font=("Courier New", 9),
                                         bg="white", fg=self.colors['text'])
        self.stack1_listbox.pack(fill="both", expand=True)

        # S2 on LEFT (RTL)
        s2_frame = tk.Frame(stacks_frame, bg=self.colors['stack'])
        s2_frame.pack(side="left", padx=5, expand=True, fill="both")
        tk.Label(s2_frame, text="S2", font=("Arial", 10, "bold"),
                bg=self.colors['stack'], fg=self.colors['text']).pack()
        self.stack2_listbox = tk.Listbox(s2_frame, height=4, width=12,
                                         font=("Courier New", 9),
                                         bg="white", fg=self.colors['text'])
        self.stack2_listbox.pack(fill="both", expand=True)

        counters_frame = tk.Frame(stacks_card, bg=self.colors['stack'])
        counters_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Label(counters_frame, text="C1:", font=("Arial", 9, "bold"),
                bg=self.colors['stack'], fg=self.colors['text']).pack(side="left", padx=5)
        self.c1_label = tk.Label(counters_frame, text="0", font=("Courier New", 11, "bold"),
                                bg=self.colors['stack'], fg=self.colors['primary'])
        self.c1_label.pack(side="left", padx=5)
        
        tk.Label(counters_frame, text="C2:", font=("Arial", 9, "bold"),
                bg=self.colors['stack'], fg=self.colors['text']).pack(side="left", padx=15)
        self.c2_label = tk.Label(counters_frame, text="0", font=("Courier New", 11, "bold"),
                                bg=self.colors['stack'], fg=self.colors['primary'])
        self.c2_label.pack(side="left", padx=5)

        # Memory (LIST) card
        mem_card = self._create_card(cards_container, "💾 זיכרון (LIST)", self.colors['memory'])
        mem_frame = tk.Frame(mem_card, bg=self.colors['memory'])
        mem_frame.pack(fill="both", expand=True, padx=5, pady=5)

        mem_scroll = ttk.Scrollbar(mem_frame)
        mem_scroll.pack(side="right", fill="y")

        self.mem_tree = ttk.Treeview(mem_frame, columns=("value",), show="tree headings",
                                     height=8, yscrollcommand=mem_scroll.set)
        mem_scroll.config(command=self.mem_tree.yview)
        self.mem_tree.heading("#0", text="Index")
        self.mem_tree.heading("value", text="Value")
        self.mem_tree.column("#0", width=80)
        self.mem_tree.column("value", width=100)
        self.mem_tree.pack(side="left", fill="both", expand=True)

        # Style for treeview
        style = ttk.Style()
        style.configure("Treeview", background=self.colors['memory'], 
                       fieldbackground=self.colors['memory'])

        for i in range(33):
            self.mem_tree.insert("", "end", text=str(i), values=(str(i),))

        # Output preview card
        out_preview_card = self._create_card(cards_container, "📤 פלט (תצוגה מהירה)", "#E8F5E9")
        self.out_preview = scrolledtext.ScrolledText(out_preview_card, height=6,
                                                     font=("Courier New", 10),
                                                     state="disabled", bg="white",
                                                     fg=self.colors['success'])
        self.out_preview.pack(fill="both", expand=True, padx=5, pady=5)

        # Bottom: Notebook (existing tabs)
        self.notebook = ttk.Notebook(right)
        right.add(self.notebook, weight=1)

        # Output tab
        out_frame = tk.Frame(self.notebook, bg=self.colors['card_bg'])
        self.notebook.add(out_frame, text="📤 פלט")
        self.out = scrolledtext.ScrolledText(out_frame, font=("Courier New", 10),
                                             bg=self.colors['card_bg'], 
                                             fg=self.colors['success'])
        self.out.pack(fill="both", expand=True, padx=5, pady=5)

        # Error tab
        err_frame = tk.Frame(self.notebook, bg=self.colors['card_bg'])
        self.notebook.add(err_frame, text="⚠ שגיאות")
        self.err = scrolledtext.ScrolledText(err_frame, font=("Courier New", 10),
                                             foreground=self.colors['error'],
                                             bg=self.colors['card_bg'])
        self.err.pack(fill="both", expand=True, padx=5, pady=5)

        # State tab
        state_frame = tk.Frame(self.notebook, bg=self.colors['card_bg'])
        self.notebook.add(state_frame, text="🔍 מצב")
        self.state = scrolledtext.ScrolledText(state_frame, font=("Courier New", 10),
                                               bg=self.colors['card_bg'], 
                                               fg=self.colors['text'])
        self.state.pack(fill="both", expand=True, padx=5, pady=5)

        # History tab
        hist_frame = tk.Frame(self.notebook, bg=self.colors['card_bg'])
        self.notebook.add(hist_frame, text="📜 היסטוריה")
        self.history = scrolledtext.ScrolledText(hist_frame, font=("Courier New", 9),
                                                 bg=self.colors['card_bg'], 
                                                 fg=self.colors['text_secondary'])
        self.history.pack(fill="both", expand=True, padx=5, pady=5)

    def _create_card(self, parent, title, bg_color=None):
        """Create a styled card frame"""
        if bg_color is None:
            bg_color = self.colors['card_bg']
        
        card = tk.LabelFrame(parent, text=title, font=("Arial", 10, "bold"),
                            bg=bg_color, fg=self.colors['text'],
                            relief=tk.RAISED, bd=2)
        card.pack(fill="both", expand=True, padx=5, pady=5)
        return card

    def _on_scrollbar(self, *args):
        self.code.yview(*args)
        self.line_numbers.yview(*args)

    def update_line_numbers(self, event=None):
        content = self.code.get("1.0", "end-1c")
        lines = content.split("\n")
        nums = "\n".join(str(i) for i in range(1, len(lines) + 1))

        self.line_numbers.config(state="normal")
        self.line_numbers.delete("1.0", "end")
        self.line_numbers.insert("1.0", nums)
        self.line_numbers.config(state="disabled")

        # sync top
        try:
            self.line_numbers.yview_moveto(self.code.yview()[0])
        except Exception:
            pass
        
        # Apply syntax highlighting
        self._apply_syntax_highlighting()
        
        # Update Python equivalent when code changes
        self.update_python_equivalent()

    def _apply_syntax_highlighting(self):
        """Apply syntax highlighting to code"""
        content = self.code.get("1.0", "end-1c")
        
        # Remove old tags
        for tag in ["comment", "keyword", "register", "number"]:
            self.code.tag_remove(tag, "1.0", "end")
        
        keywords = ["MOV", "ADD", "SUB", "MUL", "DIV", "MOD", "INC", "DEC", "CLEAR",
                   "SWAP", "PUSH", "POP", "RAND", "PRINT", "CMP", "JZ", "JNZ",
                   "GOTO", "IF", "LOOP", "HALT", "NOP"]
        registers = ["R1", "R2", "R3", "L1", "S1", "S2", "C1", "C2"]
        
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            # Comments
            for comment_char in [";", "#"]:
                if comment_char in line:
                    idx = line.index(comment_char)
                    self.code.tag_add("comment", f"{i}.{idx}", f"{i}.end")
                    line = line[:idx]  # Process only non-comment part
            
            # Keywords
            for keyword in keywords:
                start = 0
                while True:
                    idx = line.find(keyword, start)
                    if idx == -1:
                        break
                    # Check if it's a whole word
                    if (idx == 0 or not line[idx-1].isalnum()) and \
                       (idx + len(keyword) >= len(line) or not line[idx + len(keyword)].isalnum()):
                        self.code.tag_add("keyword", f"{i}.{idx}", f"{i}.{idx + len(keyword)}")
                    start = idx + 1
            
            # Registers
            for reg in registers:
                start = 0
                while True:
                    idx = line.find(reg, start)
                    if idx == -1:
                        break
                    if (idx == 0 or not line[idx-1].isalnum()) and \
                       (idx + len(reg) >= len(line) or not line[idx + len(reg)].isalnum()):
                        self.code.tag_add("register", f"{i}.{idx}", f"{i}.{idx + len(reg)}")
                    start = idx + 1
            
            # Numbers
            for match in re.finditer(r'\b\d+\b', line):
                start_idx, end_idx = match.span()
                self.code.tag_add("number", f"{i}.{start_idx}", f"{i}.{end_idx}")

    def clear_output(self):
        self.out.delete("1.0", "end")
        self.err.delete("1.0", "end")
        self.state.delete("1.0", "end")
        self.history.delete("1.0", "end")
        self.code.tag_remove("errorline", "1.0", "end")

    def copy_output(self):
        txt = self.out.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(txt)
        messagebox.showinfo("הצלחה", "הפלט הועתק ללוח.")

    def new_file(self):
        if messagebox.askyesno("חדש", "לנקות את העורך?"):
            self.code.delete("1.0", "end")
            self.clear_output()
            self.update_line_numbers()
            self.current_level = None
            self.current_example = None
            self._update_navigation_buttons()

    def open_file(self):
        filename = filedialog.askopenfilename(
            title="פתח קובץ",
            filetypes=[("Assembly files", "*.asm"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not filename:
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            self.code.delete("1.0", "end")
            self.code.insert("1.0", content)
            self.clear_output()
            self.update_line_numbers()
            self.current_level = None
            self.current_example = None
            self._update_navigation_buttons()
        except Exception as e:
            messagebox.showerror("שגיאה", f"לא ניתן לפתוח:\n{e}")

    def save_file(self):
        filename = filedialog.asksaveasfilename(
            title="שמור קובץ",
            defaultextension=".asm",
            filetypes=[("Assembly files", "*.asm"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not filename:
            return
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.code.get("1.0", "end-1c"))
            messagebox.showinfo("הצלחה", "נשמר.")
        except Exception as e:
            messagebox.showerror("שגיאה", f"לא ניתן לשמור:\n{e}")

    def load_example(self, level: str, example: str = None):
        if example is None:
            # Backward compatibility
            code = EXAMPLES.get(level) if isinstance(EXAMPLES.get(level), str) else None
            if not code:
                return
        else:
            code = EXAMPLES.get(level, {}).get(example)
            if not code:
                return

        # Save current position
        self.current_level = level
        self.current_example = example
        
        self.code.delete("1.0", "end")
        self.code.insert("1.0", code)
        self.clear_output()
        self.update_line_numbers()
        self.update_task_card()
        self.on_reset()
        self._update_navigation_buttons()
        self.update_python_equivalent()

    def on_run(self):
        self.clear_output()
        program = self.code.get("1.0", "end")
        seed_txt = self.seed_var.get().strip()
        seed = None
        if seed_txt:
            try:
                seed = int(seed_txt)
            except ValueError:
                messagebox.showerror("שגיאה", "Seed חייב להיות מספר שלם.")
                return

        try:
            max_steps = int(self.steps_var.get().strip() or "200000")
        except ValueError:
            messagebox.showerror("שגיאה", "Max steps חייב להיות מספר שלם.")
            return

        try:
            m = run_program(program, seed=seed, max_steps=max_steps, save_history=self.history_var.get())

            # output
            if m.output:
                self.out.insert("end", "=== פלט ===\n", "header")
                self.out.insert("end", "\n".join(str(x) for x in m.output) + "\n")
            else:
                self.out.insert("end", "(אין פלט)\n", "info")

            # state
            self.state.insert("end", "=== מצב סופי ===\n\n", "header")
            self.state.insert("end", f"R1 = {m.regs['R1']}\n")
            self.state.insert("end", f"R2 = {m.regs['R2']}\n")
            self.state.insert("end", f"R3 = {m.regs['R3']}\n")
            self.state.insert("end", f"L1 = {m.L1}\n\n")
            self.state.insert("end", f"C1 = {len(m.stacks['S1'])} S1 = {m.stacks['S1']}\n")
            self.state.insert("end", f"C2 = {len(m.stacks['S2'])} S2 = {m.stacks['S2']}\n\n")
            self.state.insert("end", f"ZERO = {m.flags['ZERO']} NEGATIVE = {m.flags['NEGATIVE']}\n\n")
            self.state.insert("end", f"LIST (0..9): {m.LIST[:10]} ...\n")

            # history
            if self.history_var.get() and m.execution_history:
                self.history.insert("end", "=== היסטוריה (50 אחרונים) ===\n\n")
                for i, st in enumerate(m.execution_history[-50:], 1):
                    self.history.insert("end", f"[{i}] {st['step']}\n")
                    self.history.insert("end",
                        f"  R1={st['R1']} R2={st['R2']} R3={st['R3']} L1={st['L1']} "
                        f"C1={st['C1']} C2={st['C2']} ZERO={st['ZERO']} NEG={st['NEGATIVE']}\n")

            self.notebook.select(0)
            self.update_right_cards(m)

        except AsmError as e:
            if e.line_no:
                self.code.tag_add("errorline", f"{e.line_no}.0", f"{e.line_no}.end")
                self.code.see(f"{e.line_no}.0")

            msg = "=== שגיאה ===\n\n"
            if e.line_no:
                msg += f"שורה {e.line_no}: {e}\n"
                if e.raw_line is not None:
                    msg += f"קוד מקור: {e.raw_line}\n"
            else:
                msg += f"{e}\n"
            self.err.insert("end", msg)
            self.notebook.select(1)
        except Exception as ex:
            self.err.insert("end", f"שגיאה בלתי צפויה: {ex}\n")
            self.notebook.select(1)

    def _copy_machine(self, m: Machine) -> Machine:
        """יצירת עותק עמוק של Machine"""
        new_m = Machine()
        new_m.regs = m.regs.copy()
        new_m.stacks = {"S1": m.stacks["S1"].copy(), "S2": m.stacks["S2"].copy()}
        new_m.L1 = m.L1
        new_m.LIST = m.LIST.copy()
        new_m.output = m.output.copy()
        new_m.flags = m.flags.copy()
        return new_m

    def on_step(self):
        """ביצוע צעד אחד"""
        try:
            if self.stepper is None:
                program = self.code.get("1.0", "end")
                seed_txt = self.seed_var.get().strip()
                seed = None
                if seed_txt:
                    try:
                        seed = int(seed_txt)
                    except ValueError:
                        messagebox.showerror("שגיאה", "Seed חייב להיות מספר שלם.")
                        return

                try:
                    max_steps = int(self.steps_var.get().strip() or "200000")
                except ValueError:
                    messagebox.showerror("שגיאה", "Max steps חייב להיות מספר שלם.")
                    return

                self.stepper = run_program_steps(program, seed=seed, max_steps=max_steps,
                                                 save_history=self.history_var.get())
                self.code.tag_remove("currentline", "1.0", "end")
                self.code.tag_remove("errorline", "1.0", "end")
                # נקה היסטוריה כשמתחילים stepper חדש
                self.step_history = []
                self.step_history_index = -1
                # שמור מצב התחלתי
                initial_machine = Machine()
                self.step_history.append((self._copy_machine(initial_machine), -1, 0, "", "START", []))
                self.step_history_index = 0

            # אם אנחנו באמצע היסטוריה (חזרנו אחורה), נמחק את כל מה שאחרי
            if self.step_history_index < len(self.step_history) - 1:
                self.step_history = self.step_history[:self.step_history_index + 1]
                # אם ה-stepper הוא None (כי חזרנו אחורה), נאתחל אותו מחדש
                if self.stepper is None:
                    program = self.code.get("1.0", "end")
                    seed_txt = self.seed_var.get().strip()
                    seed = None
                    if seed_txt:
                        try:
                            seed = int(seed_txt)
                        except ValueError:
                            messagebox.showerror("שגיאה", "Seed חייב להיות מספר שלם.")
                            return
                    try:
                        max_steps = int(self.steps_var.get().strip() or "200000")
                    except ValueError:
                        messagebox.showerror("שגיאה", "Max steps חייב להיות מספר שלם.")
                        return
                    self.stepper = run_program_steps(program, seed=seed, max_steps=max_steps, save_history=self.history_var.get())
                    # הריץ את ה-stepper עד שנגיע למצב הנוכחי
                    target_index = self.step_history_index
                    for _ in range(target_index):
                        try:
                            next(self.stepper)
                        except (StopIteration, AsmError):
                            break

            try:
                machine, ip, line_no, raw, op, args = next(self.stepper)
                # שמור עותק עמוק של המצב
                machine_copy = self._copy_machine(machine)
                self.step_history.append((machine_copy, ip, line_no, raw, op, args))
                self.step_history_index = len(self.step_history) - 1
                
                self.step_machine = machine
                self.highlight_current_line(line_no)
                self.update_right_cards(machine)
                self.update_python_equivalent()

                # Check for HALT
                if op == "HALT":
                    self.stepper = None
                    messagebox.showinfo("סיום", "התוכנית הסתיימה (HALT).")

            except StopIteration:
                self.stepper = None
                messagebox.showinfo("סיום", "התוכנית הסתיימה.")

        except AsmError as e:
            self.stepper = None
            self.step_machine = None
            if self.slow_running:
                self.on_slow_run()  # Stop slow run

            if e.line_no:
                self.code.tag_add("errorline", f"{e.line_no}.0", f"{e.line_no}.end")
                self.code.see(f"{e.line_no}.0")

            msg = "=== שגיאה ===\n\n"
            if e.line_no:
                msg += f"שורה {e.line_no}: {e}\n"
                if e.raw_line is not None:
                    msg += f"קוד מקור: {e.raw_line}\n"
            else:
                msg += f"{e}\n"
            self.err.insert("end", msg)
            self.notebook.select(1)

    def on_step_back(self):
        """חזרה לצעד קודם"""
        if self.step_history_index <= 0:
            # אין מצב קודם
            return
        
        # חזור למצב הקודם
        self.step_history_index -= 1
        machine_copy, ip, line_no, raw, op, args = self.step_history[self.step_history_index]
        
        # עדכן את המצב הנוכחי
        self.step_machine = machine_copy
        if line_no > 0:
            self.highlight_current_line(line_no)
        else:
            self.code.tag_remove("currentline", "1.0", "end")
        self.update_right_cards(machine_copy)
        
        # אתחל את ה-stepper כדי שנוכל להמשיך קדימה מהמצב הנוכחי
        # (ה-stepper יתאתחל מחדש ב-on_step הבא)
        self.stepper = None

    def on_reset(self):
        """איפוס מצב"""
        if self.slow_running:
            self.on_slow_run()  # Stop slow run
        self.stepper = None
        self.step_machine = None
        self.step_history = []
        self.step_history_index = -1
        self.code.tag_remove("currentline", "1.0", "end")
        
        # Reset cards to initial state
        m = Machine()
        self.update_right_cards(m)
        
        # Update Python equivalent card with current program
        self.update_python_equivalent()

    def on_slow_run(self):
        """הרצה איטית - toggle"""
        if self.slow_running:
            # Stop
            if self.after_id:
                self.after_cancel(self.after_id)
                self.after_id = None
            self.slow_running = False
            self.slow_run_btn.config(text="⏯ הרצה איטית")
        else:
            # Start
            self.slow_running = True
            self.slow_run_btn.config(text="⏸ עצור")
            try:
                delay = int(self.delay_var.get().strip() or "150")
                if delay < 50:
                    delay = 50
                elif delay > 1000:
                    delay = 1000
            except ValueError:
                delay = 150
            self._slow_run_step(delay)

    def _slow_run_step(self, delay):
        """צעד אחד בהרצה איטית"""
        if not self.slow_running:
            return

        try:
            self.on_step()
            if self.stepper is None:
                # Program ended or error
                self.slow_running = False
                self.slow_run_btn.config(text="⏯ הרצה איטית")
            else:
                self.after_id = self.after(delay, lambda: self._slow_run_step(delay))
        except Exception:
            self.slow_running = False
            self.slow_run_btn.config(text="⏯ הרצה איטית")

    def highlight_current_line(self, line_no):
        """הדגשת שורה נוכחית"""
        self.code.tag_remove("currentline", "1.0", "end")
        if line_no:
            self.code.tag_add("currentline", f"{line_no}.0", f"{line_no}.end")
            self.code.see(f"{line_no}.0")

    def update_task_card(self):
        """עדכון כרטיס המשימה"""
        content = self.code.get("1.0", "end")
        lines = content.splitlines()
        task_text = "(אין משימה בקוד הנוכחי)"
        for line in lines:
            if line.strip().startswith("; משימה:"):
                task_text = line.strip()[9:].strip()  # Remove "; משימה:"
                break
        self.task_label.config(text=task_text)

    def update_python_equivalent(self, op: str = None, args: List[str] = None):
        """עדכון כרטיס הקוד Python המקביל - מציג את כל התוכנית מתורגמת ל-Python"""
        self.python_text.config(state="normal")
        self.python_text.delete("1.0", "end")
        
        # קרא את כל הקוד מהעורך
        program_text = self.code.get("1.0", "end-1c")
        
        if not program_text.strip():
            self.python_text.insert("1.0", "# הקוד Python יופיע כאן כשתריץ צעד")
            self.python_text.config(state="disabled")
            return
        
        try:
            # פרסר את התוכנית
            instructions, labels = parse_program(program_text)
            
            if not instructions:
                self.python_text.insert("1.0", "# אין פקודות בקוד")
                self.python_text.config(state="disabled")
                return
            
            # תרגם כל פקודה ל-Python - רק את הקוד, ללא הערות
            python_lines = []
            
            for op, args, raw, line_no in instructions:
                # תרגם את הפקודה
                python_code = get_python_equivalent(op, args)
                python_lines.append(python_code)
            
            # הצג את כל הקוד Python בלבד
            full_code = "\n".join(python_lines)
            self.python_text.insert("1.0", full_code)
            
        except Exception as e:
            self.python_text.insert("1.0", f"# שגיאה בתרגום: {e}")
        
        self.python_text.config(state="disabled")

    def update_right_cards(self, machine: Machine):
        """עדכון כל הכרטיסים הימניים"""
        # Registers
        for reg in ["R1", "R2", "R3", "L1"]:
            if reg == "L1":
                value = machine.L1
            else:
                value = machine.regs[reg]
            self.reg_labels[reg].config(text=str(value))

        # Flags
        for flag_name, lbl in self.flag_labels.items():
            is_set = machine.flags[flag_name]
            lbl.config(text="כן" if is_set else "לא",
                      fg=self.colors['flag_on'] if is_set else self.colors['flag_off'])

        # Stacks
        self.stack1_listbox.delete(0, "end")
        for val in reversed(machine.stacks["S1"]):
            self.stack1_listbox.insert(0, str(val))

        self.stack2_listbox.delete(0, "end")
        for val in reversed(machine.stacks["S2"]):
            self.stack2_listbox.insert(0, str(val))

        self.c1_label.config(text=str(len(machine.stacks["S1"])))
        self.c2_label.config(text=str(len(machine.stacks["S2"])))

        # Memory (LIST)
        for i in range(33):
            item = self.mem_tree.get_children()[i]
            self.mem_tree.item(item, values=(str(machine.LIST[i]),))

        # Output preview
        self.out_preview.config(state="normal")
        self.out_preview.delete("1.0", "end")
        if machine.output:
            preview = machine.output[-20:]  # Last 20 values
            self.out_preview.insert("1.0", "\n".join(str(x) for x in preview))
        else:
            self.out_preview.insert("1.0", "(אין פלט)")
        self.out_preview.config(state="disabled")

    def next_example(self):
        """עבור לתרגיל הבא"""
        if self.current_level is None or self.current_example is None:
            return
        
        level_examples = list(EXAMPLES.get(self.current_level, {}).keys())
        if not level_examples:
            return
        
        try:
            current_index = level_examples.index(self.current_example)
            if current_index < len(level_examples) - 1:
                # יש תרגיל הבא באותה רמה
                next_example = level_examples[current_index + 1]
                self.load_example(self.current_level, next_example)
            else:
                # עבור לרמה הבאה
                all_levels = list(EXAMPLES.keys())
                current_level_index = all_levels.index(self.current_level)
                if current_level_index < len(all_levels) - 1:
                    next_level = all_levels[current_level_index + 1]
                    next_level_examples = list(EXAMPLES[next_level].keys())
                    if next_level_examples:
                        self.load_example(next_level, next_level_examples[0])
        except (ValueError, IndexError):
            pass

    def prev_example(self):
        """עבור לתרגיל הקודם"""
        if self.current_level is None or self.current_example is None:
            return
        
        level_examples = list(EXAMPLES.get(self.current_level, {}).keys())
        if not level_examples:
            return
        
        try:
            current_index = level_examples.index(self.current_example)
            if current_index > 0:
                # יש תרגיל קודם באותה רמה
                prev_example = level_examples[current_index - 1]
                self.load_example(self.current_level, prev_example)
            else:
                # עבור לרמה הקודמת
                all_levels = list(EXAMPLES.keys())
                current_level_index = all_levels.index(self.current_level)
                if current_level_index > 0:
                    prev_level = all_levels[current_level_index - 1]
                    prev_level_examples = list(EXAMPLES[prev_level].keys())
                    if prev_level_examples:
                        # טען את התרגיל האחרון ברמה הקודמת
                        self.load_example(prev_level, prev_level_examples[-1])
        except (ValueError, IndexError):
            pass

    def _update_navigation_buttons(self):
        """עדכון מצב כפתורי הניווט"""
        if self.current_level is None or self.current_example is None:
            self.prev_example_btn.config(state="disabled")
            self.next_example_btn.config(state="disabled")
            return
        
        # בדוק אם יש תרגיל קודם
        level_examples = list(EXAMPLES.get(self.current_level, {}).keys())
        all_levels = list(EXAMPLES.keys())
        
        has_prev = False
        has_next = False
        
        try:
            current_index = level_examples.index(self.current_example)
            current_level_index = all_levels.index(self.current_level)
            
            # בדוק אם יש תרגיל קודם
            if current_index > 0:
                has_prev = True
            elif current_level_index > 0:
                has_prev = True  # יש רמה קודמת
            
            # בדוק אם יש תרגיל הבא
            if current_index < len(level_examples) - 1:
                has_next = True
            elif current_level_index < len(all_levels) - 1:
                has_next = True  # יש רמה הבאה
        except (ValueError, IndexError):
            pass
        
        self.prev_example_btn.config(state="normal" if has_prev else "disabled")
        self.next_example_btn.config(state="normal" if has_next else "disabled")

    def _create_guide_section(self, parent, section):
        """יצירת סקציה מעוצבת במדריך"""
        # Section card
        card = tk.Frame(parent, bg=section.get("color", "#ffffff"), 
                       relief=tk.RAISED, bd=2)
        card.pack(fill="x", pady=10)
        
        # Header
        header = tk.Frame(card, bg=section.get("color", "#ffffff"))
        header.pack(fill="x", padx=15, pady=(15, 10))
        
        icon_title = tk.Label(header, text=section["title"], 
                             font=("Arial", 16, "bold"),
                             bg=section.get("color", "#ffffff"),
                             fg="#212121")
        icon_title.pack(anchor="w")
        
        # Separator
        sep = tk.Frame(card, height=2, bg="#BDBDBD")
        sep.pack(fill="x", padx=15, pady=5)
        
        # Content
        content_frame = tk.Frame(card, bg=section.get("color", "#ffffff"))
        content_frame.pack(fill="x", padx=15, pady=(5, 15))
        
        # Simple content
        if "content" in section:
            content_label = tk.Label(content_frame, text=section["content"],
                                    font=("Arial", 11),
                                    bg=section.get("color", "#ffffff"),
                                    fg="#424242", justify="right", wraplength=850)
            content_label.pack(anchor="e", pady=5)
        
        # Items list
        if "items" in section:
            for title, desc in section["items"]:
                item_frame = tk.Frame(content_frame, bg=section.get("color", "#ffffff"))
                item_frame.pack(fill="x", pady=8, anchor="e")
                
                title_lbl = tk.Label(item_frame, text=title,
                                   font=("Arial", 11, "bold"),
                                   bg=section.get("color", "#ffffff"),
                                   fg="#1976D2")
                title_lbl.pack(anchor="e")
                
                desc_lbl = tk.Label(item_frame, text=desc,
                                  font=("Arial", 10),
                                  bg=section.get("color", "#ffffff"),
                                  fg="#616161", justify="right")
                desc_lbl.pack(anchor="e", padx=20)
        
        # Code examples
        if "code_examples" in section:
            for title, code in section["code_examples"]:
                example_frame = tk.Frame(content_frame, bg=section.get("color", "#ffffff"))
                example_frame.pack(fill="x", pady=8, anchor="e")
                
                title_lbl = tk.Label(example_frame, text=title,
                                   font=("Arial", 11, "bold"),
                                   bg=section.get("color", "#ffffff"),
                                   fg="#1976D2")
                title_lbl.pack(anchor="e")
                
                code_frame = tk.Frame(example_frame, bg="#2E3440", relief=tk.SOLID, bd=1)
                code_frame.pack(fill="x", pady=5)
                
                code_lbl = tk.Label(code_frame, text=code,
                                  font=("Courier New", 10),
                                  bg="#2E3440", fg="#A3BE8C",
                                  justify="left", padx=10, pady=8)
                code_lbl.pack(anchor="w")
        
        # Full example
        if section.get("full_example"):
            code_frame = tk.Frame(content_frame, bg="#2E3440", relief=tk.SOLID, bd=1)
            code_frame.pack(fill="x", pady=10)
            
            code_lbl = tk.Label(code_frame, text=section["content"],
                              font=("Courier New", 11),
                              bg="#2E3440", fg="#A3BE8C",
                              justify="left", padx=15, pady=12)
            code_lbl.pack(anchor="w")
        
        # Tips list
        if "tips" in section:
            for icon, tip in section["tips"]:
                tip_frame = tk.Frame(content_frame, bg=section.get("color", "#ffffff"))
                tip_frame.pack(fill="x", pady=5, anchor="e")
                
                tip_lbl = tk.Label(tip_frame, text=f"{icon} {tip}",
                                 font=("Arial", 11),
                                 bg=section.get("color", "#ffffff"),
                                 fg="#424242")
                tip_lbl.pack(anchor="e")
        
        # Steps
        if "steps" in section:
            for icon, title, desc in section["steps"]:
                step_frame = tk.Frame(content_frame, bg=section.get("color", "#ffffff"))
                step_frame.pack(fill="x", pady=8, anchor="e")
                
                step_header = tk.Label(step_frame, text=f"{icon} {title}",
                                     font=("Arial", 12, "bold"),
                                     bg=section.get("color", "#ffffff"),
                                     fg="#1976D2")
                step_header.pack(anchor="e")
                
                step_desc = tk.Label(step_frame, text=desc,
                                   font=("Arial", 10),
                                   bg=section.get("color", "#ffffff"),
                                   fg="#616161")
                step_desc.pack(anchor="e", padx=30)

    def show_beginner_guide(self):
        """מדריך מקיף למתחיל עם UI מעוצב"""
        win = tk.Toplevel(self)
        win.title("📘 מדריך למתחיל - Assembly Studio")
        win.geometry("1000x700")
        win.configure(bg='#f5f5f5')
        
        # Header
        header = tk.Frame(win, bg='#1976D2', height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        title_label = tk.Label(header, text="📘 מדריך למתחיל", 
                              font=("Arial", 24, "bold"), 
                              bg='#1976D2', fg='white')
        title_label.pack(pady=20)
        
        subtitle = tk.Label(header, text="למד Assembly בצורה אינטראקטיבית וידידותית",
                           font=("Arial", 11),
                           bg='#1976D2', fg='#E3F2FD')
        subtitle.pack()
        
        # Main content frame with canvas for scrolling
        main_frame = tk.Frame(win, bg='#f5f5f5')
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        canvas = tk.Canvas(main_frame, bg='#f5f5f5', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#f5f5f5')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Content sections
        sections = [
            {
                "title": "🎯 מהו Assembly?",
                "color": "#E3F2FD",
                "content": """Assembly הוא שפת תכנות ברמה נמוכה שעובדת ישירות עם המעבד.
בסימולטור הזה, אנחנו לומדים את היסודות של תכנות ברמה נמוכה בצורה אינטראקטיבית וידידותית."""
            },
            {
                "title": "🔧 רכיבי המערכת",
                "color": "#FFF3E0",
                "items": [
                    ("🔢 רגיסטרים (Registers)", "R1, R2, R3 - רגיסטרים כלליים לאחסון מספרים\nL1 - רגיסטר מונה לולאות"),
                    ("📚 מחסניות (Stacks)", "S1, S2 - מחסניות לאחסון זמני (LIFO)\nC1, C2 - מונים אוטומטיים של גודל המחסניות"),
                    ("💾 זיכרון (Memory)", "LIST - מערך של 33 תאים (0-32)\nמאותחל עם הערכים 0,1,2...32"),
                    ("🚩 דגלים (Flags)", "ZERO - דולק כאשר תוצאה שווה ל-0\nNEGATIVE - דולק כאשר תוצאה שלילית"),
                ]
            },
            {
                "title": "📝 תחביר בסיסי",
                "color": "#E8F5E9",
                "code_examples": [
                    ("פקודה בסיסית", "MOV R1, 5    ; R1 = 5\nADD R1, R2   ; R1 = R1 + R2"),
                    ("תוויות", "START:           ; תווית למיקום בקוד\nGOTO START       ; קפיצה לתווית"),
                    ("הערות", "; זו הערה\n# גם זו הערה"),
                ]
            },
            {
                "title": "⚡ פקודות בסיסיות",
                "color": "#F3E5F5",
                "code_examples": [
                    ("העתקה", "MOV R1, 5        ; R1 = 5\nMOV R1, R2       ; R1 = R2"),
                    ("אריתמטיקה", "ADD R1, 5        ; R1 = R1 + 5\nSUB R1, 3        ; R1 = R1 - 3\nMUL R1, 2        ; R1 = R1 * 2"),
                    ("קיצורים", "INC R1           ; R1 = R1 + 1\nDEC R1           ; R1 = R1 - 1\nCLEAR R1         ; R1 = 0"),
                ]
            },
            {
                "title": "🐍 למידה עם Python",
                "color": "#E8F5E9",
                "content": """הכרטיס הירוק "קוד Python מקביל" מציג איך כל פקודת Assembly נראית בפייתון!

השתמש בכפתור "צעד" כדי לראות את התרגום לפייתון של כל שורה.
זה עוזר להבין בדיוק מה כל פקודה עושה.""",
                "code_examples": [
                    ("Assembly → Python", "MOV R1, 42   →   R1 = 42\nADD R1, 8    →   R1 = R1 + 8\nPRINT R1     →   print(R1)"),
                ]
            },
            {
                "title": "💡 דוגמה ראשונה",
                "color": "#FFF9C4",
                "full_example": True,
                "content": """; משימה: חשב 15 + 27 והדפס את התוצאה
MOV R1, 15       ; שים 15 ב-R1
ADD R1, 27       ; הוסף 27 ל-R1 (עכשיו R1 = 42)
PRINT R1         ; הדפס את התוצאה
HALT             ; עצור"""
            },
            {
                "title": "✅ טיפים למתחילים",
                "color": "#C8E6C9",
                "tips": [
                    ("✅", "התחל תמיד עם משימות פשוטות"),
                    ("✅", "השתמש בהערות כדי להסביר מה כל שורה עושה"),
                    ("✅", "בדוק את הרגיסטרים אחרי כל צעד בעזרת כפתור 'צעד'"),
                    ("✅", "השתמש ב-PRINT כדי לבדוק ערכים ביניים"),
                    ("✅", "שים לב לקוד Python המקביל בכרטיס הירוק!"),
                ]
            },
            {
                "title": "❌ טעויות נפוצות",
                "color": "#FFCDD2",
                "tips": [
                    ("❌", "אל תשכח HALT בסוף התוכנית"),
                    ("❌", "אל תחלק ב-0"),
                    ("❌", "שים לב למקום של היעד והמקור (תמיד יעד ראשון!)"),
                    ("❌", "אל תשכח לאתחל את L1 לפני לולאה"),
                ]
            },
            {
                "title": "🎓 התקדמות מומלצת",
                "color": "#E1BEE7",
                "steps": [
                    ("1️⃣", "רמה 1: פקודות בסיסיות", "MOV, ADD, SUB, PRINT"),
                    ("2️⃣", "רמה 2: לולאות ותנאים", "LOOP, IF, GOTO"),
                    ("3️⃣", "רמה 3: מחסניות וזיכרון", "PUSH, POP, LIST"),
                ]
            },
        ]
        
        # Create sections
        for section in sections:
            self._create_guide_section(scrollable_frame, section)
        
        # Footer with action buttons
        footer = tk.Frame(win, bg='#f5f5f5', height=70)
        footer.pack(fill="x", padx=20, pady=(0, 20))
        footer.pack_propagate(False)
        
        btn_frame = tk.Frame(footer, bg='#f5f5f5')
        btn_frame.pack(expand=True)
        
        # Start button
        start_btn = tk.Button(btn_frame, text="🚀 התחל ללמוד!",
                             command=lambda: self.load_example("תרגולים - רמה 1", "דוגמה 1: הדפס מספר"),
                             bg='#4CAF50', fg='white',
                             font=("Arial", 12, "bold"),
                             padx=30, pady=12,
                             cursor="hand2",
                             relief=tk.RAISED, bd=2)
        start_btn.pack(side="left", padx=10)
        
        # Close button
        close_btn = tk.Button(btn_frame, text="✓ סגור",
                             command=win.destroy,
                             bg='#757575', fg='white',
                             font=("Arial", 12, "bold"),
                             padx=30, pady=12,
                             cursor="hand2",
                             relief=tk.RAISED, bd=2)
        close_btn.pack(side="left", padx=10)
        
        # Hover effects
        def on_enter_start(e):
            start_btn['bg'] = '#45a049'
        def on_leave_start(e):
            start_btn['bg'] = '#4CAF50'
        def on_enter_close(e):
            close_btn['bg'] = '#616161'
        def on_leave_close(e):
            close_btn['bg'] = '#757575'
        
        start_btn.bind("<Enter>", on_enter_start)
        start_btn.bind("<Leave>", on_leave_start)
        close_btn.bind("<Enter>", on_enter_close)
        close_btn.bind("<Leave>", on_leave_close)
        
        # Cleanup on close
        def on_closing():
            canvas.unbind_all("<MouseWheel>")
            win.destroy()
        
        win.protocol("WM_DELETE_WINDOW", on_closing)

    def show_first_lesson(self):
        """שיעור ראשון עם דוגמאות קוד"""
        text = """🧾 שיעור ראשון - צעדים ראשונים ב-Assembly

=== שיעור 1: התוכנית הראשונה שלך ===

בואו נכתוב תוכנית שמדפיסה את המספר 42:

; משימה: הדפס 42
MOV R1, 42       ; שים את המספר 42 ברגיסטר R1
PRINT R1         ; הדפס את תוכן R1
HALT             ; עצור את התוכנית

מה קורה כאן?
1. MOV R1, 42 - שמים את המספר 42 ברגיסטר R1
2. PRINT R1 - מדפיסים את תוכן R1 (42)
3. HALT - עוצרים (חובה!)

=== שיעור 2: חיבור שני מספרים ===

; משימה: חשב 10 + 20
MOV R1, 10       ; R1 = 10
ADD R1, 20       ; R1 = R1 + 20 = 30
PRINT R1         ; הדפס 30
HALT

חשוב! ADD משנה את הרגיסטר הראשון:
   ADD R1, 20 אומר "הוסף 20 ל-R1"

=== שיעור 3: שימוש ביותר מרגיסטר אחד ===

; משימה: חשב (5 + 3) * 2
MOV R1, 5        ; R1 = 5
ADD R1, 3        ; R1 = 8
MOV R2, 2        ; R2 = 2
MUL R1, R2       ; R1 = R1 * R2 = 16
PRINT R1         ; הדפס 16
HALT

למה השתמשנו ב-R2?
   כי רצינו לכפול ב-2, ואת ה-2 צריך לשים איפשהו!

=== שיעור 4: העתקה בין רגיסטרים ===

; משימה: העתק ערך מ-R1 ל-R2
MOV R1, 100      ; R1 = 100
MOV R2, R1       ; R2 = R1 = 100
PRINT R2         ; הדפס 100
HALT

שים לב: MOV R2, R1 אומר "העתק מ-R1 ל-R2"
   (תמיד: יעד, מקור)

=== שיעור 5: מספר אקראי ===

; משימה: הדפס מספר אקראי
RAND R1          ; R1 = מספר אקראי בין 0 ל-32
PRINT R1         ; הדפס אותו
HALT

כל הרצה תיתן מספר אחר!
(אלא אם תשתמש ב-Seed זהה)

=== תרגילים לתרגול ===

תרגיל 1: הדפס את התוצאה של 7 * 6
תרגיל 2: חשב 100 - 35 והדפס
תרגיל 3: שים 50 ב-R1, 30 ב-R2, והדפס את סכומם
תרגיל 4: חשב (8 + 2) * 5
תרגיל 5: צור מספר אקראי, הוסף לו 10, והדפס

=== טיפים חשובים ===

✅ תמיד התחל עם תכנון - מה אני רוצה להשיג?
✅ השתמש בהערות לתכנן את הצעדים
✅ השתמש ב"צעד" כדי לראות מה קורה בכל שורה
✅ השתמש בכרטיס "🐍 קוד Python מקביל" כדי להבין את התרגום של כל פקודה
✅ אל תשכח HALT!

💡 טיפ: הכרטיס Python עוזר להבין את הלוגיקה של כל פקודה - נסה להשוות בין Assembly ל-Python!

המשך לרמה 2 כשאתה מרגיש בטוח עם הפקודות הבסיסיות!
"""
        self._show_help_window("🧾 שיעור ראשון", text, "900x700")

    def show_faq(self):
        """שאלות נפוצות"""
        text = """❓ שאלות נפוצות (FAQ)

=== שאלות כלליות ===

ש: מה ההבדל בין Assembly אמיתי לסימולטור הזה?
ת: זהו סימולטור חינוכי פשוט. Assembly אמיתי הרבה יותר מורכב ותלוי במעבד,
   אבל העקרונות זהים!

ש: למה התחביר הוא "יעד, מקור" ולא "מקור, יעד"?
ת: זה התחביר של Intel x86. יש גם ARM שעושה הפוך. בחרנו ב-Intel כי הוא נפוץ יותר.

ש: מה ההבדל בין R1, R2, R3?
ת: אין! כולם רגיסטרים כלליים. בחר מה שנוח לך.

=== שאלות על פקודות ===

ש: מה קורה אם אני משתמש ב-ADD עם שני רגיסטרים?
ת: ADD R1, R2 אומר "R1 = R1 + R2"
   R2 לא משתנה, רק R1!

ש: איך מחסנית עובדת?
ת: PUSH שם ערך על המחסנית (למעלה)
   POP מוציא את הערך העליון
   דוגמה:
     PUSH R1, S1    ; שים R1 על S1
     POP R2, S1     ; קח מ-S1 ל-R2

ש: מה זה C1 ו-C2?
ת: מונים אוטומטיים - כמה ערכים יש במחסנית.
   C1 = גודל S1
   C2 = גודל S2

ש: איך משתמשים ב-LIST?
ת: LIST זה מערך עם 33 תאים (0-32).
   דוגמאות:
     MOV R1, 5              ; R1 = 5
     MOV [LIST+R1], 100     ; LIST[5] = 100
     MOV R2, [LIST+R1]      ; R2 = LIST[5]

=== שאלות על לולאות ===

ש: איך עושים לולאה?
ת: 1. שים מספר חזרות ב-L1
   2. שים תווית בתחילת הלולאה
   3. בסוף הלולאה: LOOP <תווית>
   
   דוגמה:
     MOV L1, 5
     START:
       PRINT R1
       INC R1
     LOOP START

ש: למה הלולאה שלי אינסופית?
ת: בדוק:
   - האם שמת ערך ב-L1?
   - האם LOOP מצביע על התווית הנכונה?
   - האם יש תווית עם : בסוף?

=== שאלות על תנאים ===

ש: איך משתמשים ב-IF?
ת: IF <משתנה1> <אופרטור> <משתנה2> GOTO <תווית>
   אופרטורים: ==, !=, >, <, >=, <=
   
   דוגמה:
     IF R1 > R2 GOTO BIGGER
     PRINT R2
     GOTO END
     BIGGER:
       PRINT R1
     END:
       HALT

ש: מה ההבדל בין IF ל-CMP?
ת: CMP משווה ומעדכן דגלים (ZERO, NEGATIVE)
   IF קופץ ישירות - יותר נוח לרוב המקרים!

=== שאלות על דיבאגינג ===

ש: איך אני מוצא שגיאות?
ת: 1. השתמש ב"צעד" כדי לעבור שורה אחרי שורה
   2. בדוק את הרגיסטרים אחרי כל צעד
   3. השתמש ב-PRINT להדפיס ערכים ביניים
   4. קרא את הודעת השגיאה בכרטיסייה "שגיאות"

ש: מה זה "אינדקס LIST מחוץ לטווח"?
ת: ניסית לגשת ל-LIST[33] או יותר, או למספר שלילי.
   LIST יש רק אינדקסים 0-32!

ש: מה זה "חילוק באפס"?
ת: ניסית לחלק ב-0 - זה אסור!
   בדוק את המחלק לפני DIV או MOD.

=== שאלות על תכונות המערכת ===

ש: מה זה Seed?
ת: מספר שקובע את הרצף האקראי.
   אותו Seed = אותם מספרים אקראיים (שימושי לבדיקות!)

ש: מה זה "Max steps"?
ת: הגנה מפני לולאות אינסופיות.
   אם התוכנית עוברת 200,000 צעדים - היא נעצרת.

ש: למה לשמור היסטוריה?
ת: כדי לראות מה קרה בכל צעד.
   שימושי לדיבאגינג, אבל מאט את ההרצה.

ש: מה זה "הרצה איטית"?
ת: רואים כל צעד בזמן אמת עם עיכוב.
   מצוין ללמידה ולהבנה של מה שקורה!

ש: מה זה כרטיס "🐍 קוד Python מקביל"?
ת: כרטיס שמציג את הקוד Python המקביל לכל פקודת Assembly.
   עוזר להבין את הלוגיקה של הפקודות ולהשוות בין Assembly ל-Python.
   מופיע אוטומטית כשאתה משתמש ב"צעד" או "הרצה איטית".

=== עוד שאלות? ===

אם משהו לא ברור, נסה:
1. לקרוא את המדריך למתחיל
2. להסתכל על הדוגמאות
3. להשתמש ב"צעד" כדי לראות מה קורה
4. לנסות דברים בעצמך - זו הדרך הטובה ביותר ללמוד!
"""
        self._show_help_window("❓ שאלות נפוצות", text, "900x700")

    def show_quick_guide(self):
        text = """מדריך קצר:

- תחביר: יעד ואז ערך/מקור
  MOV R1, 5     (R1 = 5)
  ADD R1, 3     (R1 = R1 + 3)
  ADD R1, R2    (R1 = R1 + R2)

- תוויות: START: ... GOTO START
- תנאי: IF R1 > R2 GOTO BIG
- לולאה: MOV L1, 5
         LOOP START
- פלט: PRINT R1
- הערות: ; או #
"""
        self._show_help_window("מדריך קצר", text, "700x500")

    def _show_help_window(self, title, text, geometry="800x600"):
        """פונקציית עזר להצגת חלון עזרה"""
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry(geometry)
        win.configure(bg=self.colors['bg'])

        frame = tk.Frame(win, bg=self.colors['bg'])
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        box = scrolledtext.ScrolledText(frame, font=("Courier New", 10), wrap="word",
                                        bg=self.colors['card_bg'], fg=self.colors['text'])
        box.pack(fill="both", expand=True)
        box.insert("1.0", text)
        box.config(state="disabled")

        # Add close button
        btn_frame = tk.Frame(win, bg=self.colors['bg'])
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        close_btn = tk.Button(btn_frame, text="✓ סגור", command=win.destroy,
                             bg=self.colors['primary'], fg='white',
                             font=("Arial", 10, "bold"), padx=20, pady=5,
                             cursor="hand2")
        close_btn.pack(side="right")


if __name__ == "__main__":
    App().mainloop()