# Product capabilities architecture

The 0.4 product layer follows a delivery → application service → immutable domain result → repository pattern. SQLite-backed stores own persistence; pure functions handle provenance, compatibility, and policy evaluation.

## Modules

- `product/decisions.py`: workspaces, candidate snapshots, final decision digest.
- `product/provenance.py`: release provenance state classification.
- `product/portfolio.py`: dependency snapshots, changed-package detection, alert deduplication.
- `product/migration_planner.py`: Python version constraint evaluation and blocker paths.
- `product/trusted_reviews.py`: usage evidence, moderation conflict controls, audit events.
- `product/policy_gate.py`: SBOM validation, policy decisions, waiver expiry, private package filtering.
- `routers/product.py`: FastAPI delivery contracts.

## Security properties

Organization policy evaluation requires a matching `X-Organization-ID`. Review authors and package owners cannot moderate their own review objects. Expired waivers never suppress a policy violation. Provenance explicitly separates origin evidence from trustworthiness.

## Operational notes

Set `PYTHONDEPOT_PRODUCT_DB` to a writable SQLite file. The current MVP is single-process friendly; multi-instance deployment should move repositories to the main SQLAlchemy database and add transactional outbox delivery for alerts.
