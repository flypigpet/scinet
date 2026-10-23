# AI usage and validation status

**Human scientific validation: pending (`human_validation_pending`).** No independent domain-expert review, formal peer-review endorsement or validated scientific-review performance is claimed.

## Development assistance

Codex was used to assist with implementation, tests, documentation and release preparation. The project is attributed collectively to SciNet contributors; an AI tool is not listed as an author or assigned human qualifications. Automated checks and code inspection during development are not a substitute for a person's scientific review. The repository does not claim that a human domain expert has checked every line, reference or judgment.

## Optional review at runtime

The default `scinet --workspace demo run` performs local numerical work and generates a report without calling a model. AI review is requested explicitly:

```sh
python scripts/acquire.py --workspace demo
scinet --workspace demo run --ai --model MODEL_ID
```

Replace `MODEL_ID` with an actual model identifier available to your authenticated Codex CLI account. No model availability or service entitlement is implied by this example. An existing, unreviewed run containing the acquired inputs can be reviewed with `scinet --workspace demo review RUN_DIR --model MODEL_ID`.

The pipeline provides paper text, project-page text, author source, the claim list, computed statistics and author-function results to the CLI/model service. Calls use the user's authentication and allowance. Do not submit confidential or personal material without assessing whether that use is appropriate for your account and service terms.

The run stores the actual prompt, input hashes, structured response, call timing and CLI records. New runs record explicit model selection; a requested identifier is not itself proof of the provider's resolved backend. If the client does not report a resolved model, that fact must remain unknown. The original local demonstration used a default whose identity was not captured; it must not be retrospectively assigned a model name.

Authentication failures, launch errors, timeouts and invalid responses are errors, not successful reviews. SciNet does not substitute a canned response for an unavailable model. Preserve successful reviews by creating another run for a new review.

## Interpretation limits

- The scope is one known paper and one AI reviewer, not an ensemble, benchmark or blinded trial.
- The prompt explicitly directs the model to check sample versus population standard deviations, numerical rounding conventions and differences between webpage and paper claims. This is guided auditing; it does not test independent discovery of unknown defects.
- Familiarity with the example in training data cannot be excluded. Agreement with the calculations does not demonstrate broad scientific reasoning or independence.
- Numerical cross-checks support the recorded calculations. The historical 21-test suite and later software tests concern implementation behavior, not scientific-review accuracy or usefulness.
- Reference checks can validate paths, input hashes and required structure. They do not confirm that a cited page, function or sentence supports the model's interpretation. People must check those claims.
- The author-function run is limited to inspected, hash-fixed inputs. A timeout is not a security sandbox. Instructions to treat documents as untrusted are not a complete defense against prompt injection.

Reports distinguish supported, qualified, unsupported and not-tested claims. Those labels are model assessments of the supplied evidence, not publication decisions. For any subsequent human validation, document who performed it with their consent, what they checked, the version and materials, and unresolved disagreements; do not infer credentials or endorsement.
