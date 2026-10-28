"""console.py -- make stdout survive a narrow console.

Every script in this directory prints Slovak: item stems, profile names, the
reading of a result. On Windows, Python picks cp1252 for stdout whenever the
stream is NOT an interactive UTF-8 console -- a pipe, a redirected file, a
logged session, a school laptop whose code page was never changed. The script
then dies with UnicodeEncodeError, and it dies *while printing the result it
had already computed*, which is the most expensive place to lose it.

This is the third recurrence of the same defect class in this project:

    1. `server.py` crashed at startup on any non-UTF-8 console. Fixed there,
       in place, and only there.
    2. The test suite did not catch it because `run-all-tests.ps1` exports
       PYTHONIOENCODING=utf-8, which every subprocess inherits -- the harness
       masked the bug it existed to find.
    3. `measurement_plan.py` then crashed in exactly the same way under
       `run_all.py`, which (correctly) does not set that variable. The repair
       had been applied to one file rather than to the class of files.

Hence a shared module rather than a repeated block: there is now one place to
get it right, `test_analysis.py::test_console_guard` asserts every entry point
calls it, and `test_encoding_without_pythonioencoding` runs them with the
masking variable removed.
"""
from __future__ import annotations

import sys


def use_utf8() -> None:
    """Reconfigure stdout/stderr to UTF-8. Call first in every entry point.

    `errors="replace"` on purpose: a stray glyph should degrade to a question
    mark, not take down a two-minute simulation at the moment it reports.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):   # already wrapped, or not a TextIO
            pass
