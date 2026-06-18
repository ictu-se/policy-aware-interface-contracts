# Experiment Plan

## Research Questions

**RQ1. Detection effectiveness.** How much policy-bug recall is obtained by
policy-aware contract tests compared with schema validation, authentication
checks, role matrices, and single-dimension policy tests?

**RQ2. Policy dimension contribution.** Which contract dimensions explain the
detection gain: object scope, field scope, purpose and jurisdiction, audit
obligations, or endpoint inventory?

**RQ3. Causal miss explanation.** When a baseline misses a bug, which missing
oracle explains the miss: authentication, function authorization, object scope,
jurisdiction scope, purpose scope, field minimization, aggregation boundary,
audit obligation, or endpoint inventory?

**RQ4. Risk-weighted impact.** Do policy-aware tests detect more high-risk
failures, not only more failures overall?

**RQ5. Cross-domain stability.** Are the gains stable across health, citizen
services, education, and business licensing APIs?

**RQ6. Cost and scalability.** How does execution time change as the number of
policy endpoints and injected variants grows?

## Benchmark Design

The benchmark treats a policy contract as the oracle. Each endpoint policy
defines roles, purposes, object scope, field sensitivity, role-specific allowed
fields, and audit requirements. A deterministic generator creates positive and
negative test cases for valid access, wrong role, wrong jurisdiction, wrong
purpose, self access, unauthenticated access, sensitive-field probes,
aggregation boundaries, and deprecated endpoint inventory.

For each endpoint, the experiment injects one bug at a time. This gives
variant-level ground truth and supports paired comparison between methods on
the same policy-bug variants.

## Baselines

- Schema validation: checks response shape only.
- Authentication required: checks unauthenticated access only.
- Role matrix: checks coarse role authorization.
- Object-policy tests: checks object and jurisdiction conditions.
- Field-policy tests: checks response field minimization.
- Audit contract tests: checks audit side effects.
- Deprecated inventory tests: checks stale endpoint exposure.

## Proposed Method

The full policy-aware suite combines:

- function-level authorization;
- object-level authorization;
- field-level authorization and data minimization;
- purpose and jurisdiction constraints;
- audit obligations;
- deprecated endpoint inventory.

## Metrics

- precision, recall, and F1 by method;
- recall by bug family;
- risk-weighted recall;
- causal miss counts and missed risk by primary contract dimension;
- paired delta against role matrix;
- recall by domain and endpoint;
- generated test count per endpoint;
- flags per variant.
- runtime in a deterministic endpoint-scale sweep.

## Statistical Analysis

The paired comparison uses each injected bug variant as a unit. Bootstrap
confidence intervals estimate the mean proposed-minus-baseline delta for
detection and risk-flagged score.

## Next Deepening Steps

1. Investigate one miss family at a time and write the mechanism behind it.
2. Add test-minimization strategies and compare brute-force versus reduced
   contract matrices.
3. Add realistic perturbations only when they represent a concrete cause:
   incomplete role matrix, missing object predicate, weak purpose model,
   missing response minimization, missing audit side effect, or stale endpoint
   inventory.
4. Add LLM-as-a-judge only for explaining findings and classifying diagnostic
   text, while keeping injected bugs as the primary ground truth.
5. Add realistic policy overlays inspired by FHIR scopes, OpenAPI security
   schemes, and access-control policy languages.
6. Generate manuscript tables directly from result files.
