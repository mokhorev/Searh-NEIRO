# Contributing

## Local checks

```bash
pip install -e ".[dev]"
ruff check src/neirosearch/measurement src/neirosearch/measurement_cli.py tests
pytest -q
```

## Design rules

- Keep the existing CSV workflow backward compatible until the UI migration is proven on real cases.
- Every derived claim must retain evidence or an evidence span.
- New browser-provider logic must live behind a provider adapter and expose explicit error states.
- Do not add captcha bypass, stealth flags, proxy rotation, account farming or hidden submissions.
- Do not make a new LLM judge the source of truth without a labeled regression dataset.
- Prefer small, reversible changes with measurable acceptance criteria.
