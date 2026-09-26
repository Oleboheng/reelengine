# Contributing to ReelEngine

Thank you for your interest in contributing to ReelEngine.

ReelEngine is an open-source project maintained by Soflas Developments.

## Development workflow

The preferred contribution workflow is:

1. Fork the repository.
2. Clone your fork.
3. Create a dedicated branch.
4. Make your changes.
5. Test the changes locally.
6. Push the branch to your fork.
7. Open a pull request against `main`.

Please avoid making unrelated changes in the same pull request.

## Pull requests

Pull requests should explain:

* What changed
* Why it changed
* How it was tested
* Any configuration changes required
* Any security or privacy implications

For user-facing changes, screenshots or a short description of the affected workflow are helpful.

## Security-sensitive changes

Authentication, OAuth, account isolation, file access, deletion, rate limiting, and configuration changes should receive particular attention during review.

Never include:

* Production credentials
* OAuth client secrets
* Session secrets
* API keys
* Private cookies
* Production databases
* Downloaded user content

in a pull request.

## Main branch

The `main` branch represents the reviewed project state.

Contributors should use pull requests rather than attempting to push changes directly to `main`.

Maintainers may merge a pull request after reviewing the implementation and relevant tests.

## Commit messages

Please use concise commit messages that describe the change.

Examples:

```text
Add authenticated video range delivery
Fix Facebook account linking
Improve conversion error handling
Update deployment documentation
```

## Scope

ReelEngine is intentionally lightweight.

When proposing a new dependency or infrastructure component, explain why it is necessary and what operational cost it introduces.

Small, focused changes are preferred over broad rewrites.

## Code quality

Please preserve the existing security and privacy model.

In particular:

* Maintain per-user data isolation.
* Do not expose private downloaded files publicly.
* Do not commit secrets.
* Preserve authentication checks on protected routes.
* Avoid unnecessary collection of personal data.
* Preserve existing rate and resource controls unless a change is intentional and documented.

## License

By contributing to ReelEngine, you agree that your contribution may be distributed under the project's MIT License.
