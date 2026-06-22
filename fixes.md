# Cross-Platform Locale Fix Summary

## What Was Wrong

Three categories of failures, each with a different root cause:

---

### 1. Ubuntu: Missing locales (`en_GB.UTF-8`, `de_DE.UTF-8`)

**File:** `.github/workflows/commons_validator.yml`

**Problem:** Ubuntu GitHub Actions runners ship with only `C`, `C.utf8`, `POSIX`, and `en_US.utf8`
by default. Tests that call `locale.setlocale(locale.LC_ALL, "en_GB.UTF-8")` raised
`locale.Error: unsupported locale setting`.

**Fix (Linux-only YAML step):**
```yaml
- name: Install locales (Linux)
  if: runner.os == 'Linux'
  run: |
    sudo apt-get install -y locales
    sudo locale-gen en_GB.UTF-8 de_DE.UTF-8
    sudo update-locale
```

---

### 2. Windows: `locale.getdefaultlocale()` returns a non-restorable tuple

**Files:** `TimeValidatorTest.py`, `CurrencyValidatorTest.py`, `PercentValidatorTest.py`

**Problem:** On Windows, `locale.getdefaultlocale()` returns a tuple like `('en_US', 'cp1252')`.
Passing that tuple back to `locale.setlocale(locale.LC_ALL, original)` fails with
`TypeError` on Windows because Windows expects a string, not a tuple.

**Reusable pattern (pseudocode):**
```
# WRONG — breaks on Windows
original = locale.getdefaultlocale()         # returns ('en_US', 'cp1252') on Windows
...
locale.setlocale(locale.LC_ALL, original)    # TypeError: tuple not accepted on Windows

# CORRECT — works on all platforms
original = locale.setlocale(locale.LC_ALL, None)   # returns "en_US.UTF-8" (a string)
...
locale.setlocale(locale.LC_ALL, original)          # always works — string is accepted everywhere
```

`locale.setlocale(locale.LC_ALL, None)` queries the current locale **as a restorable string**
without changing it. This string can always be passed back to `setlocale` to restore state.

---

### 3. Windows: `time.tzset()` not available

**File:** `TimeValidatorTest.py`

**Problem:** `time.tzset()` is a Unix-only function that reloads the TZ environment variable.
On Windows it does not exist, causing `AttributeError: module 'time' has no attribute 'tzset'`.

**Reusable pattern:**
```python
# WRONG — crashes on Windows
time.tzset()

# CORRECT — guard with hasattr
if hasattr(time, 'tzset'):
    time.tzset()
```

---

### 4. All platforms: `CurrencyValidatorTest.testPattern` — global locale state corruption

**File:** `AbstractFormatValidator.py` (`_parse` method)

**Problem (root cause):** Every return path in `_parse` called:
```python
locale.setlocale(locale.LC_ALL, "")   # resets to system default
```
`""` means "reset to OS default", which on Ubuntu runners is the `C` locale.
- On Ubuntu: `locale.currency()` raises `ValueError` on `C` locale.
- On macOS/Windows: after each validate call, the locale was reset to `en_US` (system default).
  A subsequent `isValid1("$1,234.567", pattern)` — which should be **invalid** because the
  active locale is `en_GB` — instead found `$` matched the (now-reset-to-en_US) system currency
  symbol and returned `True` instead of `False`.

**Fix:** Save and restore the locale that was active *when `_parse` was entered*:
```python
def _parse(self, value, formatter):
    _initial_locale = locale.setlocale(locale.LC_ALL, None)  # save current locale
    ...
    # every return path now restores:
    locale.setlocale(locale.LC_ALL, _initial_locale)
    return result
```

Additionally, `locale.currency()` is wrapped in `try/except (ValueError, locale.Error)` to
handle the `C` locale gracefully if it is somehow still active.

---

## Summary Table

| Issue | OS | File changed | Pattern |
|---|---|---|---|
| Missing `en_GB`/`de_DE` locales | Ubuntu | `.github/workflows/commons_validator.yml` | Install locales in CI |
| `getdefaultlocale()` returns tuple | Windows | `*Test.py` files | Use `setlocale(LC_ALL, None)` to save |
| `time.tzset()` missing | Windows | `TimeValidatorTest.py` | Guard with `hasattr(time, 'tzset')` |
| Locale state corrupted across calls | All | `AbstractFormatValidator.py` | Save/restore `_initial_locale` in `_parse` |
