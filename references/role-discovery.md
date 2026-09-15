# Role Discovery

Use Role Discovery when the user asks to find, discover, or review emerging role names. It creates review candidates only; it never stores Trend records.

## Search period and scope

- Convert the requested period to explicit start and end dates in the configured timezone.
- When omitted, use seven calendar days including the execution date.
- If a date phrase can produce materially different ranges, ask before searching.
- Search AI, Security, and AI × Security independently.
- Limit the job market to South Korea. Search in Korean and English, and verify the actual work location from the source page.
- Search sources in this order: employer career pages first; then South Korean hiring platforms such as Saramin, JobKorea, Wanted, and Jumpit; then other job sites when needed. This list guides priority and is not a complete allowlist.

Seed names start the search but do not limit it:

- AI: Applied AI Engineer, AI Agent Engineer, Agent Engineer, LLM Engineer, Generative AI Engineer, AI Platform Engineer, Agent Platform Engineer, Agent Infrastructure Engineer, AI Evaluation Engineer.
- Security: Product Security Engineer, Application Security Engineer, Cloud Security Engineer, Security Platform Engineer, IAM Engineer, Security Engineer.
- AI × Security: AI Security Engineer, Agent Security Engineer, GenAI Security Engineer, LLM Security Engineer, AI Product Security, AI Platform Security.

Expand searches with responsibility terms such as agent, tool use, RAG, evaluation, model serving, orchestration, observability, IAM, authorization, OAuth, OIDC, sandbox, threat modeling, workload identity, policy enforcement, audit logging, data governance, and Zero Trust.

## Evidence and classification

For recruitment evidence, prioritize employer career pages and South Korean hiring platforms such as Saramin, JobKorea, Wanted, and Jumpit. Do not use this preferred-source list as a closed allowlist. Other domestic or international job sites may be used when the posting itself explicitly verifies a South Korea work location; whenever feasible, verify the listing against the employer's original careers posting. Do not make a global job aggregator the initial search target or rely on it alone when an original employer posting can be checked.

For non-recruitment context, use official documentation, company or engineering blogs, press releases, research reports, public papers, conference material, government sources, reputable editorial media, and official GitHub project material. Exclude Reddit, Hacker News, social networks, general forums, anonymous posts, and unclear community sources.

Role Discovery is a South Korea employment-market workflow. Every candidate must have at least one job posting whose work location explicitly belongs to South Korea. Remote roles qualify only when the posting explicitly allows employment from South Korea. The employer's headquarters, nationality, page language, or worldwide availability does not prove a South Korea work location. Exclude every overseas or location-unclear job posting. Non-recruitment sources may come from any country and may support responsibility or technology context, but they cannot establish that a role exists in the South Korea job market.

Require a verified original Published Date within the requested search period. A search-engine crawl date, access date, or "currently open" state is not a Published Date. Exclude a source when its original Published Date cannot be verified.

For each possible role, extract:

- exact Job title;
- explicitly stated experience level: `신입`, `경력`, `신입·경력`, or `미확인`;
- Job description;
- Responsibilities;
- Required skills;
- Team description;
- Product or domain context;
- source name, original URL, and verified Published Date.
- source type, and for a Job Posting its verified South Korea work location.

Classify from the combined evidence. Security responsibilities inside an Agent Platform role may justify AI × Security, while a Product Security role may also belong there when its actual scope includes LLM applications or agent tool abuse. Mark weak or conflicting evidence as uncertain instead of forcing a category.

## Existing-role comparison

Load Role Name and Status for all Roles DB records before evaluating new results. Normalize names with Unicode normalization, surrounding-space removal, repeated-space collapse, and case folding only. Do not use semantic title similarity as an MVP duplicate rule.

- Existing Candidate: do not create another record.
- Existing Approved: do not create another record.
- Existing Rejected: do not create another record and do not change its status.
- Duplicate observations within one run: merge responsibilities and distinct evidence URLs into one proposed Candidate.

## Candidate storage

Create a Roles DB item only when the role is new and has at least two distinct original HTTP or HTTPS evidence URLs with verified Published Dates inside the search period.

At least one of the two sources must be a South Korea Job Posting. Additional non-recruitment information may be domestic or overseas.

- Role Name: exact observed role name
- Category: recommended AI, Security, or AI × Security
- Status: Candidate
- Experience Level: explicit posting value normalized to `신입`, `경력`, `신입·경력`, or `미확인`
- Description: responsibility-based summary
- Key Responsibilities: newline-separated responsibilities
- First Discovered: execution date
- Last Reviewed: execution date
- Evidence Sources: newline-separated `Source Name — Original URL` entries
- Notes: `Job market: South Korea`, verified work location, concise discovery reason, and any uncertainty

Never alter the pre-run Approved-role snapshot, call Trend Update, or use a new Candidate to expand searches during the same run.

## Report

Report the explicit date range, `Job market: South Korea`, all three searched domains, source counts, overseas or location-unclear job-posting exclusion counts, other excluded counts, numbered new Candidates, and existing-role matches. Each candidate needs its verified South Korea work location, Experience Level, recommended Category, Description, Key Responsibilities, discovery reason, and Evidence Sources. End with a clear request for candidate approval or rejection; do not change statuses until the user responds.
