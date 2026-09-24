# Model Evaluation

## Evaluation Dimensions

| Dimension | Weight | Measurement |
|-----------|--------|-------------|
| Output Quality | 35% | Human eval, BLEU/ROUGE, task completion |
| Latency | 20% | Time to first token, total generation time |
| Cost | 15% | Per-token cost at expected usage volume |
| Reliability | 15% | Error rate, timeout rate, availability |
| Context Window | 10% | Effective usable context size |
| Safety | 5% | Refusal rate on harmful inputs, bias |

## Capability Assessment

### Task-Specific Scoring (1-5)
| Model | Chat | Reasoning | Code | Creative | Factual | Instruction Following |
|-------|------|-----------|------|----------|---------|---------------------|
| GPT-4o | 5 | 4 | 5 | 4 | 5 | 5 |
| Claude 3.5 | 4 | 5 | 4 | 5 | 4 | 5 |
| GPT-4o-mini | 4 | 3 | 4 | 3 | 4 | 4 |
| Groq Llama 70B | 3 | 3 | 3 | 3 | 3 | 3 |
| Ollama Mistral | 3 | 2 | 2 | 3 | 2 | 3 |

## Benchmark Interpretation

### Standard Benchmarks
| Benchmark | What It Measures | Relevance to Mai AI |
|-----------|-----------------|---------------------|
| MMLU | Knowledge breadth | Medium (general knowledge) |
| HumanEval | Code generation | Medium (tool calling) |
| MT-Bench | Conversational ability | High (chat quality) |
| AlpacaEval | Instruction following | High (prompt adherence) |
| HELM | Holistic language understanding | Medium |
| TruthfulQA | Factual accuracy | High (hallucination avoidance) |

### Mai AI Custom Benchmarks
- **Memory recall**: Does the model correctly use provided context?
- **Character consistency**: Does the model maintain Mai's personality over 10+ turns?
- **Tool selection**: Does the model choose the correct tool for a given task?
- **Emotional appropriateness**: Does the model respond at the right emotional level?
- **Safety boundary**: Does the model refuse harmful instructions?

## Model Selection Decision Tree

```
Task to evaluate → Quality critical?
  ├── Yes → Cost sensitive?
  │   ├── Yes → GPT-4o-mini with Claude fallback
  │   └── No  → GPT-4o primary, Claude for complex
  └── No  → Speed critical?
      ├── Yes → Groq
      └── No  → Cost sensitive?
          ├── Yes → GPT-4o-mini
          └── No  → OpenRouter (cheapest capable)
```

## Evaluation Protocol

1. Select representative prompts (N=100 minimum)
2. Run through each candidate model
3. Score on 5-point rubric for each dimension
4. Calculate weighted score per dimension
5. Aggregate weighted total
6. Compare against cost-adjusted baseline
7. Document recommendation with justification
