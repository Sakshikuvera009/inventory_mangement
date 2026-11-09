# AI-assisted development disclosure

## Tools used
ChatGPT (OpenAI).

## Usage
AI assistance was used to scaffold the Django project, propose the PostgreSQL data model, implement order and stock service logic, create API/view/template code, draft tests, SQL queries and documentation.

## Representative prompts
1. Build a Django/PostgreSQL sales order and inventory application from the supplied assignment.
2. Implement transactional stock confirmation/cancellation with row locking and movement history.
3. Add automated tests for order totals, permissions, stock rollback and all-or-nothing CSV import.

## Review
The generated code should be reviewed by the candidate, run locally, and tested against PostgreSQL. Business rules and API responses should be manually verified before submission.

## Corrections / limitations
The assignment specifies MySQL while the requested implementation uses PostgreSQL. This deviation is disclosed in README.md. The generated project has not been executed in the candidate's environment; any migration, dependency or runtime issue found during local testing must be corrected and documented.
