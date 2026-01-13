"""Executor module - Assembly code execution"""
import random
from typing import Optional, Generator, Tuple, List
from .machine import Machine, AsmError
from .parser import parse_program

def eval_condition(m: Machine, left: str, op: str, right: str) -> bool:
    lv, rv = m.get_value(left), m.get_value(right)
    if op == "==": return lv == rv
    if op == "!=": return lv != rv
    if op == ">": return lv > rv
    if op == "<": return lv < rv
    if op == ">=": return lv >= rv
    if op == "<=": return lv <= rv
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
