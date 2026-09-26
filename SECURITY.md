# Security Policy

## Reporting a vulnerability

Please do not publicly disclose sensitive security vulnerabilities in a GitHub issue.

Instead, contact the project maintainer privately with enough information to reproduce and understand the issue.

When reporting a vulnerability, please include:

* A description of the issue
* Steps to reproduce it
* The affected component or endpoint
* The potential security impact
* Any suggested mitigation, if available

Please do not include production credentials, private user data, session cookies, or other sensitive information in a report.

## What to report

Examples of security issues include:

* Authentication bypass
* Cross-user data access
* Unauthorized video/file access
* Account takeover
* OAuth identity-linking vulnerabilities
* Session handling vulnerabilities
* Secret exposure
* Remote code execution
* Injection vulnerabilities
* Container isolation failures
* Significant denial-of-service/resource-abuse vulnerabilities

## Public disclosure

Please allow the maintainer reasonable time to investigate and address a reported vulnerability before publicly disclosing technical details.

The appropriate disclosure timeline may depend on the severity and complexity of the issue.

## Security principles

ReelEngine is designed around several security principles:

* Authenticate access to user accounts.
* Isolate user-owned data.
* Keep downloaded media private.
* Avoid committing production secrets.
* Apply resource and rate limits.
* Run the production container with reduced privileges.
* Minimize unnecessary public endpoints.
* Provide account/data deletion functionality.

Security is an ongoing process. The project's implementation may evolve as new threats and deployment requirements are identified.
