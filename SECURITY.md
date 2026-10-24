# Security

SciNet is an experimental command-line research tool, not a hosted review service. The source tree includes an AI panel workflow; the `0.1.0a1` release is the earlier guided demo. There is no security-support guarantee or hardened environment for executing submitted code.

## Execution boundary

The legacy Datasaurus example extracts selected author functions after checking fixed source and seed hashes. The powerlaw example checks fixed original input hashes, retains a compatibility copy and runs selected historical-code paths. Both record changes and use bounded subprocesses. A timeout and separate process do **not** provide a security sandbox. Do not weaken the hash checks to run arbitrary code; inspect and assess new code in an appropriately isolated environment first.

The panel runs the local reproduction script explicitly selected by the operator after every review is frozen. A custom script is executable code with the permissions of that process. Model-suggested commands are not executed automatically. Input roles and filenames cannot prove that a source is authentic or free of concealed instructions.

AI review sends evidence to an authenticated Codex CLI and its model service. Panel reviewers get the selected original text; synthesis also gets original reviews and selected computation artifacts. The panel disables known CLI tools and repository instruction discovery and rejects observed tool calls or incomplete event streams. Research documents remain untrusted inputs: these controls do not establish immunity to prompt injection, absence of hidden provider context or correct judgments. Check the data you submit and the resulting references.

## Local evidence and privacy

Run folders can contain the paper, source text, model prompts, raw CLI events, errors and machine-local paths. Treat them as potentially sensitive before sharing. The public release deliberately excludes local run folders and raw AI logs. Never commit credentials or account-specific configuration.

SHA-256 verification detects changed, missing or additional files relative to a recorded inventory. The panel's local event chain and final commitment are unsigned. Save a commitment hash independently and use `scinet panel verify RUN_DIR --expected-root HASH` to compare against that reference. Without it, someone able to replace the entire bundle can also regenerate its hashes. No signature, identity verification, trusted timestamp or blockchain anchor is currently provided. Verify the source of any downloaded release independently.

## Reporting a vulnerability

For a sensitive vulnerability, use the repository's private **Report a vulnerability** option if it is available. If private reporting is not available, open a minimal issue asking the maintainers to establish a private reporting channel; do not include exploit details, credentials or private research in that public issue. No response-time or bounty commitment is offered for this preview.

Ordinary correctness bugs without sensitive details can be reported as public issues with a minimal reproduction, the version or commit, operating system and Python version.
