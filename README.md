# File Organiser

Organises a folder's loose files into category sub-folders by file type.
`detection.py` classifies files, `movement.py` moves them, and **`main.py`**
is the entry point that runs them over a whole folder.

```
usage: file_organiser [source] [target_root] [--overwrite] [--log-file PATH]

python main.py              # organise "." into "./organized"
python main.py ~/Downloads ~/Desktop/cleaned
python main.py . out --overwrite --log-file /tmp/org.log
```

Example output on the console (also mirrored to the log file):

```
Done: 2 moved, 1 unsupported, 0 duplicates, 0 failed.
```

- Unsupported, duplicate and failed files are **skipped and logged**, never
  crash the run.
- Re-run the tests with `pytest`, or read **`test_file_organiser.py`** to see
  every behaviour documented.

---

# Logging Guide

This document explains **how logging works** in this project, the **options**
available for customising it, and every **variable** you can use inside
`LOG_FORMAT`.

All logging is configured in a single place: **`logging_config.py`**. Every
other module calls `setup_logging()` and then creates a child logger with
`getChild("module_name")`, which guarantees that **all** operations land in
one shared log file with a consistent format.

---

## 1. How logging works here

```
                         ┌────────────────────────────────────────┐
 Your code calls         │  logging_config.setup_logging()        │
 logger.info(...)  ───►  │  ─ creates shared "file_organiser"     │
                         │    logger + file handler + formatter   │
                         └────────────────────────────────────────┘
                                    │
                      detection.py / movement.py
                      call setup_logging().getChild("detection")
                      or ".getChild("movement")"
                                    │
                                    ▼
                     ┌───────────────────────────┐
                     │  file_organiser.log file   │  (one shared file)
                     └───────────────────────────┘
```

- **One root logger** is shared by the whole app under the name
  `file_organiser`.
- Each module gets a **child** of it:
  - `file_organiser.detection` → used by `detection.py`
  - `file_organiser.movement`  → used by `movement.py`
- Logging is set to level **`INFO`**, so `INFO`, `WARNING`, `ERROR`, and
  `CRITICAL` records are written; `DEBUG` records are discarded.

### Example log lines

```
2026-09-08 22:01:42 - INFO    - movement.py:71  - file_organiser.movement - Destination folder ready: /tmp/dest/Images
2026-09-08 22:01:42 - WARNING - detection.py:92 - file_organiser.detection - Unsupported file type: file.xyz (extension '.xyz')
2026-09-08 22:01:42 - ERROR   - movement.py:97  - file_organiser.movement - File does not exist: /tmp/nonexistent.txt
```

Each line is produced by the `LOG_FORMAT` string below.

---

## 2. Configuration options

### 2.1 `LOGGER_NAME`

```python
LOGGER_NAME = "file_organiser"
```

The name of the **root logger**. All other loggers become children of it, so
their names in the log look like `file_organiser.detection`.

### 2.2 `LOG_FILE` — where logs are written

```python
LOG_FILE = Path(
    os.environ.get(
        "FILE_ORGANISER_LOG",
        Path(__file__).resolve().parent / "file_organiser.log",
    )
)
```

| Option | When to use it                                | Resulting log file                  |
| ------ | --------------------------------------------- | ----------------------------------- |
| (default) | No environment variable set                | `file_organiser.log` next to the source code |
| Set `FILE_ORGANISER_LOG` | When you want logs elsewhere, e.g. in CI | Examples: `/var/log/file_organiser.log`, `/tmp/app_logs.log` |

**To redirect the log file** during a run:

```bash
export FILE_ORGANISER_LOG=/var/log/file_organiser.log
python main.py            # (or whatever runs the app)
```

> The log file is **appended to**, never overwritten, so old operations stay
> in the history.

### 2.3 `setup_logging(log_file=None)` — runtime override

Tests and scripts can point logging at a **temporary** file by passing an
explicit path:

```python
from logging_config import setup_logging

setup_logging("/tmp/my_ops.log")      # instead of the default LOG_FILE
```

The function is **re-runnable**: every call removes the old handler, so no
duplicate lines ever accumulate.

### 2.4 `setup_logging` behaviour summary

| Behaviour                       | What it does                                        |
| ------------------------------- | --------------------------------------------------- |
| `logger.setLevel(logging.INFO)` | Do not record `DEBUG` messages                      |
| Remove + close old handlers     | Prevents duplicate output on repeated calls         |
| `FileHandler(file_path)`        | Creates a handler that appends to a file            |
| `handler.setFormatter(...)`     | Applies `LOG_FORMAT` + `DATE_FORMAT`                |
| `logger.propagate = False`      | Stops messages bubbling to the root Python logger   |
| `return logger`                 | Lets callers build child loggers via `getChild()`   |

---

## 3. `LOG_FORMAT` — the output layout

```python
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(name)s - %(message)s"
```

This is the **default** layout. Reading it left to right it produces:

```
<timestamp> - <LEVEL> - <file>:<line> - <logger name> - message
```

To **customise** it, change this constant in `logging_config.py`, for example:

```python
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(module)s.%(funcName)s(): %(message)s"
```

---

## 4. Variables available in `LOG_FORMAT`

These are standard **`LogRecord` attributes**. Any of them can be used inside a
format string with the syntax `%(name)s` (strings) or `%(name)d` (numbers).

| Format token      | Type   | Meaning                                                        | Example output                          |
| ----------------- | ------ | -------------------------------------------------------------- | --------------------------------------- |
| `%(name)s`        | str    | Logger name (e.g. `file_organiser.movement`)                   | `file_organiser.movement`               |
| `%(levelname)s`   | str    | Severity level name                                            | `INFO`, `WARNING`, `ERROR`              |
| `%(levelno)s`     | int    | Numeric severity                                                | `20`, `30`, `40`                        |
| `%(message)s`     | str    | The message that was logged                                     | `Moved 'a.txt' -> ...`                  |
| `%(asctime)s`     | str    | Human-readable timestamp (formatted with `DATE_FORMAT`)         | `2026-09-08 22:01:42`                   |
| `%(created)f`     | float  | Epoch time (seconds since 1970-01-01) when the record was made  | `1757354502.123456`                     |
| `%(msecs)d`       | int    | Milliseconds part of `created`                                  | `123`                                   |
| `%(relativeCreated)d` | int | Milliseconds since the `logging` module was loaded           | `42`                                    |
| `%(filename)s`    | str    | Source file name (no directory) that made the call              | `movement.py`                           |
| `%(pathname)s`    | str    | Full path to the source file                                    | `/home/user/project/movement.py`        |
| `%(module)s`      | str    | Module name (basename of `pathname` without `.py`)              | `movement`                              |
| `%(funcName)s`    | str    | Function name that called the log method                        | `move_file`                             |
| `%(lineno)d`      | int    | Line number in the source file                                  | `74`                                    |
| `%(process)d`     | int    | Process ID (PID)                                                | `12345`                                 |
| `%(processName)s` | str    | Process name                                                    | `MainProcess`                           |
| `%(thread)d`      | int    | Thread ID                                                       | `140735...`                             |
| `%(threadName)s`  | str    | Thread name                                                     | `MainThread`                            |
| `%(taskName)s`    | str    | `asyncio` task name (Python 3.12+)                              | `Task-1`                                |
| `%(exc_info)s`    | str    | Exception info (only set when `logger.exception(...)` is used)  | `None` or traceback text                |
| `%(stack_info)s`  | str    | Stack information (if requested)                                | `None` or stack text                    |

> **Tips for freshers:**
> - Use **`lex`-free mnemonics**: `%s` for strings, `%d` for integers,
>   `%f` for floats.
> - Do **not** put `%(message)s` in both `LOG_FORMAT` *and* the log call —
>   the format string already renders the message, so callers only pass the
>   raw text: `logger.info("Moved %s", destination)`.
> - Pairing `%(asctime)s` with `DATE_FORMAT` controls the date style; see
>   section 5.

---

## 5. `DATE_FORMAT` — timestamp style

```python
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
```

Used only for the `%(asctime)s` token. Codes follow `strftime`:

| Code | Meaning                  | Example   |
| ---- | ------------------------ | --------- |
| `%Y` | 4-digit year             | `2026`    |
| `%m` | Month zero-padded        | `09`      |
| `%d` | Day of month zero-padded | `08`      |
| `%H` | Hour (24h) zero-padded   | `22`      |
| `%M` | Minute zero-padded       | `01`      |
| `%S` | Second zero-padded       | `42`      |

Other handy codes: `%y` (2-digit year), `%B` (full month name), `%b` (short
month name), `%A` (weekday), `%p` (AM/PM), `%f` (microseconds).

Example alternative: `%Y-%m-%d %I:%M:%S %p` → `2026-09-08 10:01:42 PM`.

---

## 6. Log levels used by this project

| Level      | Value | Used for                                                      |
| ---------- | ----- | ------------------------------------------------------------- |
| `DEBUG`    | 10    | (not enabled) fine-grained, temporary diagnostics             |
| `INFO`     | 20    | Successful operations: folder ready, file moved               |
| `WARNING`  | 30    | Recoverable issues: duplicate refused, overwrite happening, unsupported type |
| `ERROR`    | 40    | Operations that failed: missing file, permission denied       |
| `CRITICAL` | 50    | (not used) fatal errors that stop the program                 |

To see `DEBUG` lines temporarily, change line 29 in `logging_config.py` to:

```python
logger.setLevel(logging.DEBUG)
```

---

## 7. Common questions

**Q: Why do my log lines not appear?**
A: `logger.propagate = False` is set, so the line *is* written — but only to
the file handler. Check the file at `LOG_FILE`, or look for a second handler
that prints to console (this project intentionally only writes to a file).

**Q: Why am I seeing duplicate lines?**
A: `setup_logging()` was called more than once. In this project that is safe
because old handlers are removed first on every call.

**Q: Can I add a console handler?**
```python
import sys
console = logging.StreamHandler(sys.stdout)
console.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
logger.addHandler(console)
```

**Q: How do tests avoid polluting the real log file?**
```python
setup_logging(tmp_path / "operations.log")
```
The re-run behaviour swaps the file handler to a temp file, as seen in
`test_file_organiser.py`.