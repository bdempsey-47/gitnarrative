# Security Fixes — gitnarrative

## Task 1: Prompt Injection Mitigation — COMPLETED
**File:** `gitnarrative/narrator.py`
**What was done:**
- Commit data wrapped in `<commit_data>` / `</commit_data>` XML tags
- System prompt instructs LLM to treat tag contents strictly as data, not instructions
- Commit messages truncated to 500 chars, cluster names to 200 chars via `_truncate()` helper

---

## Task 2: Exception Handling & JSON Parsing — COMPLETED
**Files:** `gitnarrative/narrator.py`, `gitnarrative/git_reader.py`
**What was done:**
- `narrator.py`: Replaced bare `except Exception` with specific `anthropic.APIError` / `json.JSONDecodeError` catches
- `narrator.py`: Fallback summary now shows generic `"[LLM narration failed]"` instead of leaking raw exception text
- `narrator.py`: Added `logging.warning()` so errors are still debuggable
- `narrator.py`: Replaced brittle `str.split`/`rsplit` fence stripping with `re.sub` patterns handling ` ```json `, partial fences, etc.
- `git_reader.py`: First `except` catches `KeyError`, `ValueError`, `GitCommandError` (expected cases); second `except Exception` logs via `logger.debug()` with traceback instead of silently passing

---

## Task 3: Input Limits (DoS Prevention) — COMPLETED
**Files:** `gitnarrative/cli.py`, `gitnarrative/git_reader.py`
**What was done:**
- Added `--max-commits` CLI option (default: 500), passed through to `read_commits()` → GitPython `iter_commits(max_count=...)`
- Warning printed when cluster count exceeds 50, suggesting `--max-commits` or narrower date range
- `--dry-run` now shows both commit and cluster counts in summary line

---

## Task 4: Date Validation — COMPLETED
**File:** `gitnarrative/cli.py`
**What was done:**
- Added `_validate_date()` accepting `YYYY-MM-DD` and `YYYY-MM-DDTHH:MM:SS` formats
- Clear error on invalid format: `"Invalid --since date '...'. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS."`
- Cross-validation: errors if `--since` is after `--until`
