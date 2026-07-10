# Security policy

## Report a vulnerability

Do not publish API keys, cookies, browser-profile data, client evidence or a working exploit in a public issue.

Use GitHub's private vulnerability reporting / Security Advisories for this repository. Include:

- affected version or commit;
- operating system and Python version;
- reproduction steps with synthetic data;
- expected and observed behavior;
- impact and suggested mitigation, if known.

## Sensitive areas

Pay special attention to:

- `.env` and provider credentials;
- persistent browser profiles and cookies;
- evidence files, screenshots, MHTML/HAR and DOM excerpts;
- path traversal in evidence storage;
- prompt/answer content rendered in Streamlit or Markdown;
- CSV formula injection in Excel exports;
- SQLite files containing client observations;
- automatic external actions.

## Supported version

Until formal releases are established, only the latest `main` branch and open release-candidate pull request receive fixes.

## Project boundaries

Search-NEIRO must not add captcha bypass, proxy/account farming, hidden submissions, autonomous publication or credential harvesting. Security reports proposing those mechanisms will not be accepted as product features.
