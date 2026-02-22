# Part 1: Data Integration Strategy (The "Plumbing")

GovPreneurs AI Product Case Study — Auto-Proposal Engine

---

## 1. Analyze the Source: SAM.gov Get Opportunities API

**Endpoint:** [SAM.gov Get Opportunities Public API (v2)](http://open.gsa.gov/api/get-opportunities-public-api/#)

- **Base URL:** `https://api.sam.gov/opportunities/v2/search`
- **Auth:** Public API key required (query param `api_key`). Rate limits apply by role (federal / non-federal / general).
- **Pagination:** Synchronous; mandatory `postedFrom` and `postedTo` (MM/dd/yyyy), max 1-year range. `limit` (max 1000) and `offset` for page index.
- **Scope:** Returns the **latest active version** of each opportunity only. All version history requires SAM.gov Data Services, not this API.
- **Update cadence (per GSA docs):** Active notices are updated **daily**; archived notices are updated **weekly**.
- **No webhooks or push:** The API is pull-only. There is no documented way to subscribe to changes or receive webhooks for new/modified notices.

**Notable request params for ingestion:** `postedFrom`, `postedTo`, `ptype` (procurement type), `typeOfSetAside`, `ncode` (NAICS), `rdlfrom`/`rdlto` (response deadline range), `limit`, `offset`.

**Critical response details:** Each opportunity has a `description` field that is a **URL** to the full notice text (scope of work). To download content, we must call that URL with the API key. Attachments are in `resourceLinks` (array of URLs). Set-Aside is in `typeOfSetAside` (code) and `typeOfSetAsideDescription` (human-readable).

---

## 2. Define the Schema: GovPreneurs Opportunity (minimal)

**Schema file:** [`../schemas/govpreneurs_opportunity.schema.json`](../schemas/govpreneurs_opportunity.schema.json) — trimmed to required + useful-or-maybe-useful fields only.

### Rationale: Fields We Keep (minimal schema)

| Category | Fields | Why |
|----------|--------|-----|
| **Identity** | `noticeId`, `solicitationNumber`, `title` | Dedup, re-fetch, display. Title used by AI for search and context. |
| **Matching** | `naicsCodes`, `naicsCode`, `typeOfSetAside`, `typeOfSetAsideDescription` | Match user NAICS and eligibility (Veteran/SDB/8a/WOSB). |
| **Timing** | `postedDate`, `responseDeadLine`, `archiveDate`, `active` | Prioritization, due-soon logic, filter closed/archived. |
| **Scope / AI** | `description`, `scopeOfWorkText`, `resourceLinks` | RAG: fetch from `description` URL → `scopeOfWorkText`; chunk attachments from `resourceLinks` for proposal drafting. |
| **Agency / Place** | `fullParentPathName`, `placeOfPerformance` | Agency and geography filter. |
| **Trust / UX** | `uiLink`, `pointOfContact` (fullName, email, phone) | Citations and POC for compliance. |
| **Notice type** | `type` | Filter by Solicitation, Presolicitation, etc. |
| **Ingestion** | `ingestedAt` | Freshness and idempotent upserts. |

`scopeOfWorkText` is **not** from SAM.gov; we populate it by fetching the `description` URL. Same for downloading/chunking `resourceLinks` (e.g. RFP PDFs) for RAG.

---

## 3. Ingestion Strategy: Keeping Data Fresh and Handling Modified Notices

### No webhooks

SAM.gov does not offer webhooks or push for new or updated opportunities. We **must poll** the API.

### Recommended approach: Poll + upsert by `noticeId`

1. **Sliding window by posted date**
   - Use `postedFrom` and `postedTo` with a fixed window (e.g. last 30 or 90 days for “active” opportunities). Stay within the API’s 1-year max range.
   - Paginate with `limit` (e.g. 1000) and `offset` until no more results.
   - Map each SAM.gov opportunity into the **GovPreneurs Opportunity** schema (set `ingestedAt` = now).

2. **Upsert by `noticeId`**
   - Use `noticeId` as the unique key in our store (e.g. MongoDB).
   - For each record: if `noticeId` exists, **overwrite** with the latest payload; otherwise insert. This handles **modified** notices (e.g. deadline or scope change): the next time we fetch that notice, we get the latest version and replace our copy.

3. **Re-fetch “modified” notices**
   - The public API returns only the latest active version per notice. We cannot see revision history.
   - **Strategy:** On every run, we re-fetch the same date window (or a rolling window). Any change on SAM.gov (deadline, description URL, set-aside, etc.) will appear in the response and be written over the previous record when we upsert. So “modified” notices are handled by **re-polling and upserting**, not by a separate “modified” API.

4. **Cadence**
   - Align with GSA’s update policy: run at least **daily** for active opportunities. Higher frequency (e.g. every 6–12 hours) improves freshness for last-minute deadline or scope changes.

5. **Optional: incremental by `noticeId`**
   - To catch amendments for older postings without re-scanning full history: maintain a list of “watch” `noticeId`s (e.g. opportunities our users saved or applied to) and periodically re-fetch those by `noticeId` (e.g. `?noticeid=...&limit=1`) and upsert. This complements the date-window poll.

6. **Description and attachments**
   - **Description:** After upserting the opportunity, call the `description` URL (with API key) to get the full notice text; store in `scopeOfWorkText` (and/or chunk into a vector store for RAG).
   - **Attachments:** Similarly, download `resourceLinks`, store or chunk for RAG, and optionally attach metadata (e.g. `noticeId`, section) for citations.

### Summary

| Question | Answer |
|----------|--------|
| Do we poll or use webhooks? | **Poll.** No webhooks available. |
| How do we handle “modified” notices? | **Re-poll** the same (or rolling) date window and **upsert by `noticeId`**; the latest response overwrites our stored record. |
| How do we keep data fresh? | **Daily** (or more frequent) job that polls by `postedFrom`/`postedTo`, paginates, upserts by `noticeId`, then refreshes `scopeOfWorkText` and attachments for RAG. |
