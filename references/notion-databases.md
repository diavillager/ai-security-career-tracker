# Notion database setup

Use this procedure only under the confirmed AI Security Career Tracker project page.

## Roles DB

Create Roles DB first with these properties:

| Property | Type | Allowed values or purpose |
| --- | --- | --- |
| Role Name | Title | Canonical role name |
| Category | Select | AI, Security, AI × Security |
| Status | Select | Candidate, Approved, Rejected |
| Experience Level | Select | 신입, 경력, 신입·경력, 미확인 |
| Description | Rich text | Short role definition |
| Key Responsibilities | Rich text | Evidence-based responsibilities |
| First Discovered | Date | First verified discovery date |
| Last Reviewed | Date | Most recent review date |
| Evidence Sources | Rich text | Original evidence URLs |
| Notes | Rich text | Review notes |

## Trends DB

Create Trends DB only after Roles DB has a verified data source identifier.

| Property | Type | Allowed values or purpose |
| --- | --- | --- |
| Title | Title | Source title |
| Summary | Rich text | Concise source summary |
| Key Insight | Rich text | Role-relevant finding |
| Source Type | Select | Job Posting, Report, Article, Research, Official |
| Source Name | Rich text | Publisher or organization |
| Original URL | URL | Original source URL |
| Published Date | Date | Verified publication date |
| Collected Date | Date | Collection date |
| Related Roles | Relation | Roles DB data source |
| Domain | Select | AI, Security, AI × Security |

## Safe creation and reuse

1. Fetch the connected Notion identity and the configured project page.
2. Read `config.toml` with `load_database_config`.
3. If both identifiers exist, fetch both data sources and verify their titles and required properties. Reuse them when valid.
4. If neither identifier exists, inspect the project page for existing databases with the exact titles before creating anything.
5. Create Roles DB, verify its schema, then create Trends DB with a one-way `Related Roles` relation to the Roles data source.
6. Verify both schemas and persist both identifiers together. Never commit `config.toml`.

Stop and ask the user for direction when only one identifier is present, a saved database cannot be fetched, a schema does not match, or an existing same-title database is ambiguous. Do not create a replacement automatically.
