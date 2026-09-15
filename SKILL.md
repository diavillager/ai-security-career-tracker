---
name: ai-security-career-tracker
description: Discover emerging AI, security, and AI security roles, manage user approval, and collect recent trends for approved roles in Notion. Use for role discovery, candidate review, approval changes, or approved-role trend updates; do not use for general career advice or unrelated security news.
---

# AI Security Career Tracker

Track changing roles across AI, Security, and AI × Security while keeping role discovery separate from trend collection.

## Current development boundary

The MVP foundation, Notion database setup, and Role Discovery are implemented. Approval changes and trend collection are not implemented yet; do not claim otherwise.

## Fixed product rules

- Interpret natural-language requests as Role Discovery, approval or rejection, or Trend Update.
- Use the most recent 7 days when the user does not specify a period.
- Use Codex web search as the default search provider.
- Treat search-provider access as a replaceable boundary rather than embedding provider-specific assumptions throughout the workflow.
- Keep AI, Security, and AI × Security in the default search scope.
- Limit Role Discovery and every recruitment or job-market item to verified South Korea work locations. Overseas non-recruitment information remains allowed.
- Prioritize company career pages and South Korean hiring platforms such as Saramin, JobKorea, Wanted, and Jumpit. Treat these as preferences, not a closed allowlist.
- Store new roles as Candidate. Never use them for Trend Update before the user approves them.
- Keep Rejected roles as review history instead of deleting them.
- Preserve the original source URL for every saved role or trend.
- Use normalized or canonical URL equality as the only MVP duplicate rule.

Read [references/product-requirements.md](references/product-requirements.md) before implementing or changing a feature.

## Notion database setup

Read [references/notion-databases.md](references/notion-databases.md) whenever creating, checking, or reconnecting the project databases.

- Confirm the connected workspace and project page before any write.
- Inspect `config.toml` first. When both database identifiers are saved, fetch and reuse them.
- When neither identifier is saved, inspect the project page for existing Roles DB and Trends DB before creating anything.
- Treat a partial configuration, inaccessible saved identifier, or mismatched database as a stopping condition. Report it instead of creating a replacement.
- Create Roles DB first, then create Trends DB with `Related Roles` pointing to the Roles data source.
- Save both data source identifiers together with `python src/ai_security_career_tracker/notion_databases.py` only after both schemas have been verified.

## Role Discovery

Read [references/role-discovery.md](references/role-discovery.md) for search planning, evidence requirements, Notion field mapping, and reporting.

- Use the latest 7 calendar days ending today when the request has no period.
- Load every existing Role Name and Status before searching. Candidate, Approved, and Rejected records all block creation of another Candidate with the same normalized role name.
- Search AI, Security, and AI × Security independently with seed names and responsibility terms. Seeds guide discovery but never form a whitelist.
- Search the South Korea job market in Korean and English. Start with company career pages and South Korean hiring platforms such as Saramin, JobKorea, Wanted, and Jumpit; this is a priority order, not a closed allowlist.
- Use other domestic or international job sites only when the posting itself explicitly verifies a South Korea work location. When feasible, validate those listings against the employer's original careers posting instead of relying on a global aggregator alone.
- Use allowed official or editorial sources for supporting context. Overseas sources are allowed only for non-recruitment information; exclude community and social sources.
- Require an original Published Date inside the search period. Do not substitute a crawl date, access date, or current-open status; exclude undated content.
- Evaluate title, responsibilities, skills, team, and product context together. Do not classify from the title alone.
- Store only evidence-backed new roles with Status `Candidate`; require at least two distinct sources, including at least one verified South Korea job posting, and preserve every supporting source name and original URL.
- Keep the Approved-role snapshot from before the run unchanged. Do not start Trend Update or use newly created Candidates as search terms in the same run.
- Report numbered candidates and existing-role matches separately so the user can review them.

## Authorization boundaries

- Confirm the connected Notion workspace and target project page before creating or changing databases.
- Do not create a replacement database when a saved database identifier is missing or inaccessible; report the condition and ask the user to identify the existing database.
- Do not add Candidate or Rejected roles to Trend Update queries.
- Do not merge a feature branch into `main` without explicit user approval.
- Never store credentials in repository files, logs, commits, or pull request text.
