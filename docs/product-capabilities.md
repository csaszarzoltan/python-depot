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

## Version 0.5 delivery layer

`python_depot.product_ui` converts the product-domain services into deterministic, accessible HTML view models. `python_depot.routers.product_pages` exposes the workspaces through FastAPI without moving domain decisions into page handlers.

The interface follows these rules:

- one primary task per screen;
- explicit empty, partial, success, failure, and recovery states;
- origin evidence is never presented as proof of package safety;
- tenant or conflict-of-interest restrictions remove unsafe actions;
- desktop uses persistent navigation and multi-column details, while narrow viewports use a single-column flow and sticky primary action;
- user-controlled values are escaped before HTML output.
