"""Translator module - Assembly to Python"""
from typing import List

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