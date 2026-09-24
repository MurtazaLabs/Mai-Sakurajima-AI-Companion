# Experiment Design

## A/B Testing Framework

### Hypothesis Template
```
Hypothesis: [Change] will improve [metric] by [effect size].
Null Hypothesis: [Change] has no effect on [metric].
Success Metric: [primary KPI]
Guardrail Metrics: [metrics that must not degrade]
Population: [user segment]
```

### Sample Experiment: Embedding Model Upgrade
```yaml
hypothesis: Upgrading embedding model v1→v2 will improve recall@5 by 5%
null_hypothesis: v2 embedding has no effect on recall@5
success_metric: recall@5
guardrail_metrics:
  - retrieval_latency (must not increase >20ms)
  - cache_hit_rate (must not decrease >5%)
  - response_time p95 (must not increase >100ms)
population: 50% of users (random split)
duration: 7 days
sample_size: 500 queries per group (minimum)
statistical_method: two-tailed t-test, α=0.05, β=0.20
```

## Statistical Methods

| Method | When to Use | Minimum Sample |
|--------|-------------|----------------|
| Two-tailed t-test | Comparing means of two groups | 30 per group |
| Chi-squared | Comparing categorical outcomes | 50 per group |
| Mann-Whitney U | Non-normal distributions | 20 per group |
| ANOVA | Comparing >2 groups | 20 per group |
| Bayesian A/B | Continuous learning, no fixed horizon | Any (updates posterior) |

## Experiment Lifecycle

### 1. Design Phase
- Define hypothesis and success metrics
- Select statistical method
- Calculate required sample size
- Define guardrail metrics
- Document experiment plan

### 2. Implementation Phase
- Instrument metric collection
- Implement feature flag / random assignment
- Run canary (5% traffic, 24h)
- Verify data collection integrity
- Ramp to full experiment traffic

### 3. Observation Phase
- Monitor guardrail metrics daily
- Check for data quality issues
- Log any incidents or anomalies
- Do NOT peek at results (trust the sample size)

### 4. Analysis Phase
- Apply statistical test
- Check for Simpson's paradox (segment analysis)
- Evaluate practical significance (not just statistical)
- Document findings and recommendations
- Decide: ship, roll back, or iterate

## Common Pitfalls

- **Peeking**: Looking at results before sample size is reached
- **Multiple comparisons**: Testing too many metrics inflates false positive rate
- **Novelty effect**: Users behave differently with new features (first 3 days)
- **Selection bias**: Uneven assignment or non-random sampling
- **Survivorship bias**: Only analyzing active users, ignoring churned ones

## Experiment Report Template

```
Experiment: [Name]
Status: [In Progress / Concluded / Cancelled]
Duration: [Start] → [End]
Sample: [N] users / [N] events

Results:
  Success Metric: [before vs after, p-value, effect size]
  Guardrail 1: [before vs after, p-value]
  Guardrail 2: [before vs after, p-value]

Conclusion: [Ship / Roll back / Iterate]
Recommendation: [Next steps]
```
