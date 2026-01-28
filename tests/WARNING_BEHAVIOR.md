### Overview of Flags in pytest

- **`-s`** or **`--capture=no`**: Disables output capturing completely - all prints/logs show immediately
- **`-v`** or **`--verbose`**: Shows test names in verbose format, but still captures output (unless combined with `-s`)
- **`-vv`**: Even more verbose (shows local variables on failure)

## Warnings Behavior

### Default Warning Display

By default, pytest:
1. **Collects** all warnings during test execution
2. **Shows them at the end** of the test run in a summary
3. Only shows warnings that match certain filters

### Making Warnings Appear Immediately

To make `warnings.warn()` appear in console **without `-s` or `-v`**, configured pytest to:

1. **Always show UserWarning**: Added `-W always::UserWarning` to `pytest.ini`
2. **Filter warnings**: Added `filterwarnings = always::UserWarning` to `pytest.ini`

This means:
- ✅ Warnings will appear **immediately** when issued
- ✅ No need for `-s` or `-v` flags
- ✅ Warnings are shown in real-time during test execution

### Configuration in pytest.ini

```ini
[pytest]
addopts = 
    -s
    -v
    --strict-markers
    -W always::UserWarning    # Always show UserWarning immediately
    --tb=short                 # Short traceback format
filterwarnings =
    always::UserWarning        # Always show UserWarning (alternative method)
```

### Warning Filter Options

- `always::UserWarning` - Always show UserWarning
- `error::UserWarning` - Convert UserWarning to errors
- `ignore::UserWarning` - Ignore UserWarning
- `default::UserWarning` - Use default behavior (show at end)

### Example

```python
import warnings

def test_example():
    warnings.warn("This warning will appear immediately!", UserWarning)
    # Test continues...
```

With the configured `pytest.ini`, this warning will appear in the console immediately when the test runs, even without `-s` or `-v`.

## Summary

| Output Type | Default Behavior | Show Without Flags |
|------------|-----------------|-------------------|
| `print()` | Hidden (captured) | Use `-s` flag |
| `logging` | Hidden (captured) | Use `-s` flag or configure handlers |
| `warnings.warn()` | Shown at end | Configure `-W always::UserWarning` in pytest.ini ✅ |

**For warnings specifically**: The `pytest.ini` is now configured to show `UserWarning` immediately without needing any flags!
