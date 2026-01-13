"""Machine module"""
import re
from typing import Optional, List, Dict, Any, Tuple

class AsmError(Exception):
    def __init__(self, message: str, line_no: Optional[int] = None, raw_line: Optional[str] = None):
        super().__init__(message)
        self.line_no = line_no
        self.raw_line = raw_line

class Machine:
    def __init__(self):
        self.regs = {"R1": 0, "R2": 0, "R3": 0}
        self.stacks = {"S1": [], "S2": []}
        self.L1 = 0
        self.LIST = list(range(33))
        self.output: List[int] = []
        self.flags = {"ZERO": False, "NEGATIVE": False}
        self.execution_history: List[Dict[str, Any]] = []

    def get_counter(self, name: str) -> int:
        if name == "C1": return len(self.stacks["S1"])
        if name == "C2": return len(self.stacks["S2"])
        raise AsmError(f"מונה לא ידוע: {name}")

    def update_flags(self, value: int):
        self.flags["ZERO"] = (value == 0)
        self.flags["NEGATIVE"] = (value < 0)

    def get_value(self, token: str) -> int:
        token = token.strip()
        if token in self.regs: return int(self.regs[token])
        if token in ("C1", "C2"): return int(self.get_counter(token))
        if token == "L1": return int(self.L1)
        if re.fullmatch(r"-?\d+", token): return int(token)
        raise AsmError(f"ערך לא חוקי: {token}")

    def _parse_list_expr(self, expr: str) -> Tuple[str, int]:
        expr = expr.strip()
        m = re.fullmatch(r"\[LIST\s*\+\s*([A-Za-z0-9\-]+)\s*\]", expr)
        if not m: raise AsmError(f"ביטוי LIST שגוי: {expr}")
        inside = m.group(1)
        if inside in ("R1", "R2", "R3"): return inside, int(self.regs[inside])
        if inside == "L1": return inside, int(self.L1)
        if re.fullmatch(r"-?\d+", inside): return inside, int(inside)
        raise AsmError(f"אינדקס LIST לא חוקי: {inside}")

    def read_list(self, expr: str) -> int:
        src, idx = self._parse_list_expr(expr)
        if not (0 <= idx < len(self.LIST)):
            raise AsmError(f"אינדקס LIST מחוץ לטווח: {idx}")
        return int(self.LIST[idx])

    def write_list(self, expr: str, value: int):
        src, idx = self._parse_list_expr(expr)
        if not (0 <= idx < len(self.LIST)):
            raise AsmError(f"אינדקס LIST מחוץ לטווח: {idx}")
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
            "step": step_info, "R1": self.regs["R1"], "R2": self.regs["R2"],
            "R3": self.regs["R3"], "L1": self.L1,
            "C1": len(self.stacks["S1"]), "C2": len(self.stacks["S2"]),
            "S1": self.stacks["S1"].copy(), "S2": self.stacks["S2"].copy(),
            "ZERO": self.flags["ZERO"], "NEGATIVE": self.flags["NEGATIVE"],
        })
