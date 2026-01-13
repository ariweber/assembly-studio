"""Parser module"""
import re
from typing import List, Tuple, Dict
from .machine import AsmError

TOKEN_SPLIT = re.compile(r"[,\s]+")

def parse_program(text: str) -> Tuple[List[Tuple[str, List[str], str, int]], Dict[str, int]]:
    instructions, labels = [], {}
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.split(";", 1)[0].split("#", 1)[0].strip()
        if not line: continue
        if line.endswith(":"):
            label = line[:-1].strip()
            if not label: raise AsmError("תווית ריקה", line_no=line_no, raw_line=raw)
            key = label.upper()
            if key in labels: raise AsmError(f"תווית כפולה '{label}'", line_no=line_no, raw_line=raw)
            labels[key] = len(instructions)
            continue
        parts = [p for p in TOKEN_SPLIT.split(line) if p]
        if not parts: continue
        op, args = parts[0].upper(), parts[1:]
        instructions.append((op, args, raw, line_no))
    return instructions, labels
