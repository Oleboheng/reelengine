# ReelEngine

**Soflas ReelEngine** is a lightweight, self hosted web application for authenticated Instagram Reel conversion and private video management.

It is designed as a small, security conscious service that can run on infrastructure controlled by Soflas Developments while keeping each user's account, conversion history, usage limits, and downloaded files isolated from other users.

The project is open source under the **MIT License**.

## Project status

ReelEngine is currently a working web application focused on Instagram Reel conversion.

### Currently implemented

* Email/password authentication
* Google authentication
* Facebook authentication
* Facebook identity linking to an existing ReelEngine account
* Per-user data isolation
* Daily conversion limits
* Conversion concurrency limits
* Private conversion history
* Automatic history retention
* Authenticated video playback and download
* HTTP range-based video playback
* Account deletion
* Data-deletion workflow
* Privacy and data-deletion information pages
* Conversion outcome classification
* Request and login rate limiting
* Secure session cookies
* Security response headers
* Container level hardening
* Health monitoring
* Mobile friendly web interface
* Reel history story viewer
* Soflas branding
* Soflas favicon and application icon
* Open Graph and social sharing metadata

## What ReelEngine does

A user can create an account, authenticate, submit an Instagram Reel URL, and have ReelEngine process the video.

The current public deployment is available at:

https://reels.soflasdevelopments.co.za

The public application includes Soflas branding, browser favicon support, and social sharing metadata for platforms that generate link previews.

Completed conversions are associated with the authenticated user who created them.

The application deliberately limits usage rather than treating the service as an unrestricted public downloader. This helps control resource consumption and makes the service more suitable for public deployment on infrastructure operated by Soflas Developments.

## Architecture

ReelEngine intentionally keeps its production architecture small.

```text
Browser
   │
   ▼
HTTPS / reverse proxy
   │
   ▼
FastAPI application
   │
   ├── Authentication
   │     ├── Email/password
   │     ├── Google
   │     └── Facebook
   │
   ├── Conversion processing
   │
   ├── Per-user history
   │
   ├── Authenticated video delivery
   │
   └── Account/data deletion
   │
   ├── SQLite database
   │
   └── Private downloaded video files
```

The application currently uses:

* Python
* FastAPI
* SQLite
* Docker
* FFmpeg
* Vanilla JavaScript
* HTML/CSS

There is intentionally no Redis or PostgreSQL dependency in the current ReelEngine architecture.

## Authentication and account isolation

ReelEngine supports:

* Email/password accounts
* Google OAuth
* Facebook OAuth

OAuth identities are associated with ReelEngine accounts.

Facebook linking is designed to link a Facebook identity to an already authenticated ReelEngine account rather than silently creating duplicate accounts.

If an external identity is already associated with another ReelEngine account, the application does not automatically merge those accounts.

User-owned history and downloaded files are scoped to the authenticated ReelEngine account.

## Usage controls

The production configuration supports resource controls including:

* Daily download/conversion limit
* Maximum concurrent conversions
* Maximum file size
* Maximum video duration
* History retention limit
* API rate limiting
* Login/OAuth rate limiting

These controls are configurable through environment variables.

The example configuration intentionally contains placeholders rather than production credentials.

## Security

ReelEngine is designed to run as a public service while limiting unnecessary exposure and resource abuse.

The production container currently uses several hardening measures, including:

* Non-root application user
* Read-only container filesystem
* Temporary filesystem for `/tmp`
* Dropped Linux capabilities
* `no-new-privileges`
* Process limit
* Memory limit
* CPU limit
* Health checks
* Disabled FastAPI documentation endpoints
* Secure session cookies
* HTTP security headers
* Content Security Policy
* HSTS when HTTPS cookies are enabled
* Request body size limits
* API rate limiting
* Login rate limiting
* Authenticated file access

Private runtime data such as the production environment file, database, downloaded videos, and Instagram cookie material is intentionally excluded from the public repository.

## Video delivery

Completed videos are not exposed as unrestricted public files.

Video playback and downloads are authenticated and associated with the current ReelEngine user.

The application supports HTTP range requests so browsers can seek through videos without requiring the entire file to be downloaded first.

Access checks are performed before private video content is served.

## Data deletion

ReelEngine provides an account deletion workflow.

The application includes dedicated privacy and data-deletion information pages describing the current service behavior.

Account deletion is implemented as an application workflow rather than simply removing a browser session.

## Configuration

Production configuration is supplied through environment variables.

Copy the example configuration and provide values appropriate for the deployment environment:

```bash
cp .env.example .env
```

Important configuration areas include:

```text
SESSION_SECRET
PUBLIC_BASE_URL
DAILY_DOWNLOAD_LIMIT
HISTORY_LIMIT
MAX_CONCURRENT_DOWNLOADS
MAX_FILE_SIZE_MB
MAX_DURATION_SECONDS
RATE_LIMIT_PER_MINUTE
LOGIN_RATE_LIMIT_PER_MINUTE
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
FACEBOOK_CLIENT_ID
FACEBOOK_CLIENT_SECRET
```

Production secrets should never be committed to Git.

## Running locally

Build and start the application with Docker Compose:

```bash
docker compose build reelengine
docker compose up -d reelengine
```

The application exposes its internal HTTP service on port `8000` inside the Docker network.

A health endpoint is available at:

```text
/health
```

The exact public URL depends on the deployment's reverse-proxy configuration.

## Repository structure

```text
.
├── app/
│   ├── auth.py
│   ├── config.py
│   ├── db.py
│   ├── deletion.py
│   ├── downloads.py
│   ├── email.py
│   ├── oauth.py
│   └── web/
│       ├── components/
│       ├── pages/
│       ├── public/
│       └── styles/
├── Dockerfile
├── docker-compose.yml
├── index.html
├── main.py
├── requirements.txt
└── .env.example
```

## Roadmap

The current application is intentionally focused on getting the core ReelEngine service right before expanding its scope.

### Browser extension

A future version may provide a browser extension that can interact with ReelEngine's authenticated API.

The goal would be to make the workflow more convenient than manually copying URLs into the web application.

### Additional platforms

The longer-term direction is to investigate support for additional social/video platforms.

This is a planned capability, not a claim that ReelEngine currently supports every platform.

Platform support will depend on technical feasibility, available interfaces, and the applicable terms and policies of each platform.

### Multi-platform media workflows

Future versions may evolve ReelEngine from a single-platform converter into a broader media-processing service with a consistent API and user experience.

### Self-hosted deployments

The architecture is intentionally lightweight so that ReelEngine can potentially be deployed by other developers on their own infrastructure.

### Soflas-hosted infrastructure

Soflas may provide a managed/hosted version of ReelEngine using Soflas-operated infrastructure.

The open-source project and a potential hosted service can therefore evolve independently.

## Open source

ReelEngine is released under the MIT License.

You are free to use, modify, distribute, and commercially use the software subject to the terms of that license.

The MIT License does not grant rights to use the Soflas name, logo, trademarks, or branding as if a project or service were officially operated or endorsed by Soflas Developments.

## Responsible use

ReelEngine is software for processing media URLs.

Users are responsible for ensuring that their use of the software and the content they process complies with applicable law and the terms and policies of relevant third-party services.

The project does not grant users rights to content hosted by third parties.

## Contributing

Contributions are welcome.

The preferred workflow is:

1. Fork the repository.
2. Create a feature or fix branch.
3. Make the change.
4. Test the change.
5. Open a pull request against `main`.
6. Wait for review before merging.

The `main` branch is intended to represent the reviewed project state.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for more information.

## Security

If you discover a security vulnerability, please do not publish sensitive details in a public issue.

See [`SECURITY.md`](SECURITY.md) for the responsible disclosure process.

## License

ReelEngine is licensed under the MIT License.

Copyright (c) 2026 Soflas Developments.
