# Source code

- `pi_digits.py`: deterministic Chudnovsky binary-splitting π digit generator; standard library only.
- `generate_forecast.py`: builds all five model portfolios and canonical pre-draw payload.
- Tests are in `tests/`.

The forecast generator intentionally fails closed on invalid history, post-cutoff history rows, invalid ticket structure, insufficient π digits, or duplicate portfolios. It does not publish commitments by itself. Commitment is a separate operation using the commit–reveal ledger workflow.
