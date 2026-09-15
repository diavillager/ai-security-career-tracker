# MVP product requirements

## Product split

Role Discovery finds new role names and stores only new roles as Candidate. Trend Update uses only roles whose current status is Approved. A Candidate discovered in a Role Discovery run must not be added recursively to searches in the same run.

## Default behavior

- Accept natural-language requests without requiring JSON or command-line syntax.
- Apply the latest 7-day period when no period is specified.
- Search AI, Security, and AI × Security by default.
- Use Codex web search as the initial provider.
- Evaluate responsibilities, skills, team context, and product context rather than relying on a job title alone.
- Exclude community sources such as Reddit, Hacker News, social networks, general forums, and anonymous posts from the MVP.
- Exclude content whose original Published Date cannot be verified.

## Notion structure

Create one Roles database and one Trends database under the confirmed project page. Save their identifiers after the first creation and reuse them. Never create duplicate databases merely because saved identifiers are unavailable.

Roles must support Role Name, Category, Status, Description, Key Responsibilities, First Discovered, Last Reviewed, Evidence Sources, and Notes.

Trends must support Title, Summary, Key Insight, Source Type, Source Name, Original URL, Published Date, Collected Date, Related Roles, and Domain.

## Implementation order

1. Project foundation
2. Notion databases and identifier reuse
3. Role Discovery
4. Candidate approval and rejection
5. Trend Update
6. URL normalization and duplicate prevention
7. Classification and role relations
8. Final Skill packaging

Each feature is developed from the latest merged `main` in a separate feature branch. Run relevant tests, push the branch, and open a pull request. Merge only after explicit user approval.

## MVP exclusions

- Semantic event deduplication
- Automatic approval of new roles
- Recursive searching from newly discovered Candidates
- Community and social content
- Direct newsletter inbox collection
- Scheduled runs and automatic weekly reports
- Salary, growth-rate, or company-level hiring trend analysis
- Automatic GitHub repository creation
