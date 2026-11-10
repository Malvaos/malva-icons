"""Plumbing shared by the measured check suites of the new icon families (glyphs, tiles, theme, avatars).
Same conventions as check_objects.py: a check returns (label, ok, text, value, (lo, hi)); the label carries its
threshold; Agg prints one line per check, with the worst value in the set or the icons that failed."""
from __future__ import annotations

from pathlib import Path


def num(name, v, lo=None, hi=None, fmt=".3f", label=None):
    ok = (lo is None or v >= lo) and (hi is None or v <= hi)
    lab = label or name + "(" + ("" if lo is None else f">={lo:{fmt}}") + ("" if hi is None else f"<={hi:{fmt}}") + ")"
    return (lab, bool(ok), f"{v:{fmt}}", float(v), (lo, hi))


def flag(name, ok, text=""):
    return (name, bool(ok), text, None, (None, None))


class Agg:
    def __init__(self):
        self.rows: dict[str, list] = {}

    def add(self, icon, results):
        for r in results:
            self.rows.setdefault(r[0], []).append((icon,) + tuple(r[1:]))

    def lines(self, scope="icons"):
        out, failed = [], 0
        for name, rs in self.rows.items():
            bad = [r for r in rs if not r[1]]
            vals = [(r[3], r[0]) for r in rs if r[3] is not None]
            lo, hi = rs[0][4]
            if bad:
                failed += 1
                info = f"{len(bad)} of {len(rs)} failed: " + "; ".join(f"{r[0]} {r[2]}" for r in bad[:10]) + (" ..." if len(bad) > 10 else "")
            elif vals:
                if lo is not None and hi is not None:
                    a, b = min(vals), max(vals)
                    info = f"{len(rs)} icons, range {a[0]:.3f} ({a[1]}) .. {b[0]:.3f} ({b[1]})"
                elif lo is not None:
                    a = min(vals)
                    info = f"{len(rs)} icons, lowest {a[0]:.3f} ({a[1]})"
                else:
                    b = max(vals)
                    info = f"{len(rs)} icons, highest {b[0]:.3f} ({b[1]})"
            else:
                info = f"{len(rs)} icons ok"
            out.append((f"{'FAIL' if bad else 'PASS'}  {scope:<8} {name}  {info}", not bad))
        return out, failed


class Report:
    def __init__(self):
        self.lines, self.failed, self.total = [], 0, 0

    def extend(self, lines):
        for text, ok in lines:
            self.total += 1
            self.failed += 0 if ok else 1
            self.lines.append(text)

    def add(self, scope, results):
        for r in results:
            name, ok, info = r[0], r[1], r[2]
            self.extend([(f"{'PASS' if ok else 'FAIL'}  {scope:<8} {name}  {info}", ok)])


def fails(res, prefix):
    """(did a check whose label starts with `prefix` fail?, what it said)."""
    names = [f"{r[0].split('(')[0]} = {r[2]}" if r[2] else r[0].split("(")[0] for r in res if not r[1] and r[0].startswith(prefix)]
    return bool(names), "; ".join(names)[:170]


def finish(rep, neg, header, report_path=None):
    text = "\n".join([f"{header}  checks: {rep.total}  failed: {rep.failed}  "
                      f"negative tests (a broken input must fail): {sum(1 for n in neg if n[1])}/{len(neg)}"]
                     + rep.lines + ["", "negative tests"]
                     + [f"{'caught ' if ok else 'MISSED '} {n}  {info}" for n, ok, info in neg]) + "\n"
    if report_path:
        Path(report_path).write_text(text)
    return text
