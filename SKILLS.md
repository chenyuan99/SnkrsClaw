# SnkrsClaw Skills

This file documents useful Claude Code skills and workflows for developing and maintaining the SnkrsClaw project.

## Setup

Install dependencies:
```bash
pip install -r requirements.txt
```

Verify drivers are executable (Linux/macOS):
```bash
chmod +x bin/geckodriver-linux bin/chromedriver-linux
```

## Running the Bot (Dry Run)

Test without purchasing (`--purchase` flag omitted):
```bash
python3 main.py \
  --username myemail@gmail.com \
  --password abc123 \
  --url <shoe-url> \
  --shoe-size 10 \
  --shoe-type M \
  --driver-type firefox \
  --page-load-timeout 2
```

## Running the Bot (Live Purchase)

> **Warning:** Only use `--purchase` when you intend to buy.

```bash
python3 main.py \
  --username myemail@gmail.com \
  --password abc123 \
  --url <shoe-url> \
  --shoe-size 10 \
  --shoe-type M \
  --cvv 123 \
  --driver-type firefox \
  --headless \
  --purchase \
  --page-load-timeout 2 \
  --release-time "2026-04-01 10:00:00"
```

## Debugging

Capture a screenshot and page HTML after a run:
```bash
python3 main.py ... --screenshot-path debug.png --html-path debug.html
```

Run with the browser window visible (non-headless):
```bash
python3 main.py ... --dont-quit
# (omit --headless to keep the browser open for inspection)
```

## Experimental Features

The `experimental.py` script contains work-in-progress features. Run it the same way as `main.py`:
```bash
python3 experimental.py --username ... --password ... --url ... --shoe-size 10
```

## Common Options Reference

| Option | Description |
|---|---|
| `--username` | Nike account email |
| `--password` | Nike account password |
| `--url` | Product URL from nike.com/launch |
| `--shoe-size` | Numeric size (e.g. `9`, `10.5`) |
| `--shoe-type` | `M`, `W`, `Y`, or `C` |
| `--cvv` | Credit card CVV |
| `--driver-type` | `firefox` (default) or `chrome` |
| `--headless` | Run browser in background |
| `--login-time` | Pause until this time before logging in |
| `--release-time` | Pause until this time before purchasing |
| `--num-retries` | Retry count on failure |
| `--shipping-option` | `STANDARD`, `TWO_DAY`, or `NEXT_DAY` |
| `--purchase` | Actually submit the purchase |

## Code Structure

| File | Purpose |
|---|---|
| `main.py` | Primary bot — login, size selection, checkout |
| `experimental.py` | Experimental / in-progress features |
| `bin/` | Bundled Selenium WebDrivers (Chrome & Firefox) |
| `requirements.txt` | Python dependencies |
