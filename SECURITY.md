# Security

SciNet 0.1.0a1 is an alpha command-line research prototype, not a hosted review service. There is no security-support guarantee or hardened environment for executing submitted code.

## Execution boundary

The numerical example extracts a small, fixed set of author functions only after checking the accepted source and seed hashes. It records compatibility edits and runs a bounded subprocess. A timeout and separate process do **not** provide a security sandbox. Do not weaken the hash checks to run arbitrary code; inspect and assess new code in an appropriately isolated environment first.

The optional AI review sends evidence to an authenticated Codex CLI and the configured model service. Research documents are untrusted inputs. Prompt instructions and structured-output validation do not establish immunity to prompt injection or guarantee correct judgments. Check the data you submit and the resulting references.

## Local evidence and privacy

Run folders can contain the paper, source text, model prompts, raw CLI events, errors and machine-local paths. Treat them as potentially sensitive before sharing. The public release deliberately excludes local run folders and raw AI logs. Never commit credentials or account-specific configuration.

SHA-256 verification detects changed, missing or additional files relative to a recorded manifest. It does not authenticate a maintainer or author, establish an external timestamp, or prevent someone from replacing both the evidence and its manifest. Verify the source of any downloaded release independently.

## Reporting a vulnerability

For a sensitive vulnerability, use the repository's private **Report a vulnerability** option if it is available. If private reporting is not available, open a minimal issue asking the maintainers to establish a private reporting channel; do not include exploit details, credentials or private research in that public issue. No response-time or bounty commitment is offered for this preview.

Ordinary correctness bugs without sensitive details can be reported as public issues with a minimal reproduction, the version or commit, operating system and Python version.
