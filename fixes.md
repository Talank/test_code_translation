# Cross-Platform Test Failure Fixes

Commit: `3e6f578` — five files changed, three categories of failure.

---

## 1. Ubuntu: Missing locales

**File:** `.github/workflows/commons_validator.yml`

**Problem:** Ubuntu GitHub Actions runners only have `C`, `C.utf8`, `POSIX`, `en_US.utf8`
by default. Tests calling `locale.setlocale(locale.LC_ALL, "en_GB.UTF-8")` or
`"de_DE.UTF-8"` raised `locale.Error: unsupported locale setting`.

**Fix:** Added a Linux-only CI step to install and generate the missing locales:

```yaml
- name: Install locales (Linux)
  if: runner.os == 'Linux'
  run: |
    sudo apt-get install -y locales
    sudo locale-gen en_GB.UTF-8 de_DE.UTF-8
    sudo update-locale
```

---

## 2. Windows: `locale.getdefaultlocale()` returns an unrestorable tuple

**Files:** `TimeValidatorTest.py`, `CurrencyValidatorTest.py`, `PercentValidatorTest.py`

**Problem:** On Windows, `locale.getdefaultlocale()` returns a tuple like `('en_US', 'cp1252')`.
Passing that tuple back to `locale.setlocale(locale.LC_ALL, original)` in `tearDown`/cleanup
raises a `TypeError` because `setlocale` expects a string on Windows.

**Reusable pattern:**

```python
# WRONG — breaks on Windows (getdefaultlocale returns a tuple, not a string)
original = locale.getdefaultlocale()
# ... change locale ...
locale.setlocale(locale.LC_ALL, original)   # TypeError on Windows

# CORRECT — works on all platforms
original = locale.setlocale(locale.LC_ALL, None)  # None = query without changing; returns a string
# ... change locale ...
locale.setlocale(locale.LC_ALL, original)          # always works
```

`locale.setlocale(locale.LC_ALL, None)` reads the current locale as a restorable string
without changing anything. That string is always accepted back by `setlocale`.

---

## 3. Windows: `time.tzset()` is Unix-only

**File:** `TimeValidatorTest.py`

**Problem:** `time.tzset()` reloads the `TZ` environment variable. It exists only on Unix.
On Windows it raises `AttributeError: module 'time' has no attribute 'tzset'`.

**Reusable pattern:**

```python
# WRONG — crashes on Windows
time.tzset()

# CORRECT — guard with hasattr
if hasattr(time, 'tzset'):
    time.tzset()
```

---

## 4. All OSes: `CurrencyValidator._parse` used stale locale for fallback symbol lookup

**File:** `CurrencyValidator.py`

**Problem:** After `super()._parse(value, formatter, locale_)` returned `None`, the fallback
called `locale.currency()` using whatever locale happened to be active at that point
(the system default — `en_US` on macOS/Windows, `C` on Ubuntu). The correct locale for the
fallback should be the one the caller intended (`locale_`), not the ambient global state.

On macOS/Windows with system default `en_US`, the fallback found `$` in the test value
`"$1,234.567"` even when the test had set `en_GB` as active, causing `isValid` to return
`True` when it should have been `False`.

**Fix:** Save the locale before `super()._parse` resets it, then explicitly set the correct
locale for the symbol lookup:

```python
def _parse(self, value, formatter, locale_):
    saved_locale = locale.setlocale(locale.LC_ALL, None)   # save before super() resets it
    parsedValue = super()._parse(value, formatter, locale_)
    if parsedValue is not None or not isinstance(formatter, str):
        return parsedValue

    effective_locale = locale_ if locale_ is not None else saved_locale
    try:
        locale.setlocale(locale.LC_ALL, effective_locale)
        currency_symbol = locale.currency(0, symbol=True, grouping=False)[0]
    except locale.Error:
        return parsedValue   # locale not supported on this system (e.g. C locale on Ubuntu)
    if value and currency_symbol in value:
        parsedValue = value.replace(currency_symbol, "")
    return parsedValue
```

---

## Summary

| # | Problem | OS | File | Fix |
|---|---|---|---|---|
| 1 | `en_GB`/`de_DE` locales not installed | Ubuntu | `commons_validator.yml` | `locale-gen` in CI |
| 2 | `getdefaultlocale()` returns tuple | Windows | `*ValidatorTest.py` (×3) | Use `setlocale(LC_ALL, None)` |
| 3 | `time.tzset()` missing | Windows | `TimeValidatorTest.py` | Guard with `hasattr` |
| 4 | Wrong locale used for currency fallback | All | `CurrencyValidator.py` | Save locale before `super()._parse` |
