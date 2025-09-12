# Security Policy

## Supported Versions

We actively maintain `main`. Report vulnerabilities against this branch.

## Reporting a Vulnerability

- Please email the maintainers or open a private security advisory on GitHub.
- Do not create public issues for vulnerabilities.
- We will acknowledge receipt within 48 hours and provide a remediation timeline.

## Secrets & Credentials

- Never commit secrets. Use `.env` locally and secret managers in CI/CD. Example files are provided:
  - Root: `.env.example`
  - Frontend: `apps/web/.env.local.example`
- If a secret is committed:
  1. Rotate the secret immediately (OpenRouter, R2, Clerk, etc.).
  2. Remove the secret from the repository and purge from git history if necessary.
  3. Add or update ignore rules to prevent future commits.

### Purging leaked secrets from Git history

Option A: BFG Repo-Cleaner (fast)

1. Download BFG: https://rtyley.github.io/bfg-repo-cleaner/
2. Remove a specific key pattern from history:

   java -jar bfg.jar --replace-text sensitive.txt .git

   Where `sensitive.txt` contains lines like:

   OPENROUTER_API_KEY==>REDACTED
   R2_SECRET_ACCESS_KEY==>REDACTED

3. Or remove all `.env` files from history:

   java -jar bfg.jar --delete-files ".env" --delete-files ".env.local" .git

4. Cleanup and force-push:

   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   git push --force

Option B: git filter-repo (official successor to filter-branch)

1. Install: https://github.com/newren/git-filter-repo
2. Remove files from entire history:

   git filter-repo --path .env --path .env.local --invert-paths

3. Force-push:

   git push --force

Notify collaborators to re-clone (history is rewritten).

## OpenRouter Attribution

- We set `HTTP-Referer` from `OPENROUTER_HTTP_REFERER` or `SERVICE_BASE_URL`.
- Ensure these reflect your actual domain in production.

## Transport & CORS

- Use HTTPS in production.
- Set `CORS_ALLOW_ORIGINS` to explicit allowed origins.

## Rate Limiting & Auth

- Enable API auth behind Kong/Clerk.
- Adjust rate limiting via env (`ENABLE_INAPP_RATE_LIMIT`, `RATE_LIMIT_*`).
