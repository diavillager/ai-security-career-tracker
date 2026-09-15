---
name: ai-security-career-tracker
description: Discover emerging AI, security, and AI security roles, manage user approval, and collect recent trends for approved roles in Notion. Use for role discovery, candidate review, approval changes, or approved-role trend updates; do not use for general career advice or unrelated security news.
---

# AI Security Career Tracker

Track changing roles across AI, Security, and AI × Security while keeping role discovery separate from trend collection.

## Current development boundary

The MVP foundation and Notion database setup are implemented. Role discovery, approval changes, and trend collection are not implemented yet; do not claim otherwise.

## Fixed product rules

- Interpret natural-language requests as Role Discovery, approval or rejection, or Trend Update.
- Use the most recent 7 days when the user does not specify a period.
- Use Codex web search as the default search provider.
- Treat search-provider access as a replaceable boundary rather than embedding provider-specific assumptions throughout the workflow.
- Keep AI, Security, and AI × Security in the default search scope.
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
- Save both data source identifiers together with `python -m ai_security_career_tracker.notion_databases` only after both schemas have been verified.

## Authorization boundaries

- Confirm the connected Notion workspace and target project page before creating or changing databases.
- Do not create a replacement database when a saved database identifier is missing or inaccessible; report the condition and ask the user to identify the existing database.
- Do not add Candidate or Rejected roles to Trend Update queries.
- Do not merge a feature branch into `main` without explicit user approval.
- Never store credentials in repository files, logs, commits, or pull request text.
