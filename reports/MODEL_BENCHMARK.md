# MODEL BENCHMARK — Phase 1.2 (laptop side)

Date: 2026-08-12 09:36 UTC
Harness: `scripts/model_benchmark.py` · Part B tasks: 8 sampled (seed 7) from `training_data/instruction_pairs.jsonl` (domain split: finance=8)
System prompt: production `dourmouse.dispatch.system_message(registry)` · Ollama http://127.0.0.1:11434
Part A = strict-JSON obedience (5 fixed tasks); Part B = open answers on real tasks.

> Honest limits: keyword coverage is a weak quality proxy; `dourmouse-finetuned` may be in-sample on these pairs (same corpus) — treat its numbers as an upper bound.

## Summary

| model | A valid-JSON | B refusal | B avg coverage | B avg latency (s) | B avg tokens |
|---|---|---|---|---|---|
| dourmouse-finetuned | 100% | 12% | 0.05 | 33.1 | 2318 |
| qwen3:8b | 60% | 0% | 0.06 | 77.7 | 2651 |
| gemma4:12b | 20% | 0% | 0.03 | 216.3 | 3150 |

## Per-task detail
### dourmouse-finetuned

- **A0** [-] ok=True lat=8.2s tok=143 — Summarize the risk of holding a leveraged FX position overnight in JSO
  > {"plan": ["Monitor market volatility", "Prepare for potential margin calls"], "risks": ["Market move
- **A1** [-] ok=True lat=2.8s tok=133 — List the three steps to run a backtest on usdjpy_drift_k1 in JSON.
  > {"plan": ["Load historical USDJPY price data", "Apply drift model with k=1 parameter", "Generate and
- **A2** [-] ok=True lat=11.1s tok=146 — What guardrails should a paper-trading loop enforce? Answer in JSON.
  > {"plan": ["Initialize trading environment", "Set up risk management rules", "Implement entry and exi
- **A3** [-] ok=True lat=10.0s tok=137 — Propose a weekly routine for maintaining a strategy lab in JSON.
  > {"plan": ["Review current projects", "Update project status", "Identify next steps", "Schedule meeti
- **A4** [-] ok=True lat=10.3s tok=135 — Explain what NOT CONFIGURED means for a tool result in JSON.
  > {"plan": ["Identify which configuration settings are missing or incorrect", "Review documentation to
- **B0** [finance] ref=False cov=0.103 lat=109.9s tok=2498 — this is the essay prompt:Is it possible and desirable to raise taxatio
  > The question "Is it possible and desirable to raise taxation on the top 1%?" invites a nuanced discu
- **B1** [finance] ref=False cov=0.013 lat=7.2s tok=2147 — So can we use the mcp on Atlas
  > I'm not sure what you mean by "mcp" in this context. Could you clarify or provide more details about
- **B2** [finance] ref=False cov=0.025 lat=15.5s tok=2235 — do it for this file, contoinue from the last bar of music, i.e 22/23, 
  > To achieve your request, I need more details about the current state and structure of the file. Coul
- **B3** [finance] ref=False cov=0.007 lat=5.8s tok=2138 — points for para 2, assuming we are chosing the dfirst option
  > The second paragraph of what document or text are you referring to? Could you please provide more co
- **B4** [finance] ref=False cov=0.058 lat=14.4s tok=2179 — bollinger bands?, ema?
  > Bollinger Bands and Exponential Moving Average (EMA) are technical indicators used in financial anal
- **B5** [finance] ref=False cov=0.148 lat=90.8s tok=3046 — video features an interview with Matteo Conti, a quantitative hedge fu
  > ### Summary of Matteo Conti's "Prop Firm Golden Ticket" Strategy  #### Core Components: - **Strategy
- **B6** [finance] ref=False cov=0.0 lat=3.0s tok=2114 — give points for those 3
  > Could you please clarify which three things you'd like to give points for?
- **B7** [finance] ref=True cov=0.056 lat=17.8s tok=2191 — convert into tabliture
  > I'm sorry, but I need more context to understand what you want to convert into tablature. Could you 
### qwen3:8b

- **A0** [-] ok=False lat=99.3s tok=590 — Summarize the risk of holding a leveraged FX position overnight in JSO
  > 
- **A1** [-] ok=True lat=84.8s tok=549 — List the three steps to run a backtest on usdjpy_drift_k1 in JSON.
  > {"plan": ["Load historical data for USD/JPY including drift and k1 parameters", "Define backtesting 
- **A2** [-] ok=True lat=77.9s tok=495 — What guardrails should a paper-trading loop enforce? Answer in JSON.
  > {"plan": ["Enforce maximum risk per trade to prevent overexposure", "Implement position sizing limit
- **A3** [-] ok=False lat=95.9s tok=587 — Propose a weekly routine for maintaining a strategy lab in JSON.
  > 
- **A4** [-] ok=True lat=93.2s tok=545 — Explain what NOT CONFIGURED means for a tool result in JSON.
  > {"plan": ["Check the tool's configuration files for missing or incorrect settings", "Verify required
- **B0** [finance] ref=False cov=0.096 lat=113.2s tok=2594 — this is the essay prompt:Is it possible and desirable to raise taxatio
  > **Is it possible and desirable to raise taxation on the top 1%?**    **Key Considerations:**   1. **
- **B1** [finance] ref=False cov=0.031 lat=58.7s tok=2522 — So can we use the mcp on Atlas
  > The term "MCP" isn't recognized in the current toolset for the Atlas project. Please clarify what "M
- **B2** [finance] ref=False cov=0.051 lat=117.9s tok=2912 — do it for this file, contoinue from the last bar of music, i.e 22/23, 
  > **Headline:** I'll help you continue the music file from bar 22/23 with a falling guitar motif.    *
- **B3** [finance] ref=False cov=0.013 lat=41.5s tok=2381 — points for para 2, assuming we are chosing the dfirst option
  > I need more context to determine which "para 2" and "dfirst option" you're referring to. Could you c
- **B4** [finance] ref=False cov=0.084 lat=85.5s tok=2673 — bollinger bands?, ema?
  > **Bollinger Bands & EMA Explained**   Bollinger Bands are a technical indicator consisting of a midd
- **B5** [finance] ref=False cov=0.125 lat=111.6s tok=3308 — video features an interview with Matteo Conti, a quantitative hedge fu
  > **Headline:** Matteo Conti's "Prop Firm Golden Ticket" Strategy Summary   **Detail:** The strategy, 
- **B6** [finance] ref=False cov=0.0 lat=36.6s tok=2347 — give points for those 3
  > I need clarification on which three items or entities you'd like to assign points to. Could you plea
- **B7** [finance] ref=False cov=0.056 lat=56.9s tok=2473 — convert into tabliture
  > The term "tabliture" is ambiguous — does it refer to musical tablature (e.g., guitar tabs), a tabula
### gemma4:12b

- **A0** [-] ok=False lat=118.9s tok=589 — Summarize the risk of holding a leveraged FX position overnight in JSO
  > 
- **A1** [-] ok=True lat=108.9s tok=586 — List the three steps to run a backtest on usdjpy_drift_k1 in JSON.
  > { "plan": [ "Define the specific trading parameters and entry/exit logic for the usdjpy_drift_k1 sym
- **A2** [-] ok=False lat=105.5s tok=590 — What guardrails should a paper-trading loop enforce? Answer in JSON.
  > {   "plan": [     "Implement maximum position size constraints (e.g., no more than 10% of total capi
- **A3** [-] ok=False lat=99.8s tok=588 — Propose a weekly routine for maintaining a strategy lab in JSON.
  > 
- **A4** [-] ok=False lat=100.5s tok=589 — Explain what NOT CONFIGURED means for a tool result in JSON.
  > 
- **B0** [finance] ref=False cov=0.096 lat=223.1s tok=3139 — this is the essay prompt:Is it possible and desirable to raise taxatio
  > It is both possible and desirable to raise taxation on the top 1%, depending on which economic theor
- **B1** [finance] ref=False cov=0.0 lat=186.7s tok=3127 — So can we use the mcp on Atlas
  > 
- **B2** [finance] ref=False cov=0.0 lat=249.9s tok=3170 — do it for this file, contoinue from the last bar of music, i.e 22/23, 
  > 
- **B3** [finance] ref=False cov=0.0 lat=261.4s tok=3133 — points for para 2, assuming we are chosing the dfirst option
  > 
- **B4** [finance] ref=False cov=0.142 lat=238.6s tok=3022 — bollinger bands?, ema?
  > Bollinger Bands and Exponential Moving Averages (EMAs) are fundamental technical analysis tools used
- **B5** [finance] ref=False cov=0.0 lat=229.2s tok=3676 — video features an interview with Matteo Conti, a quantitative hedge fu
  > 
- **B6** [finance] ref=False cov=0.0 lat=128.5s tok=2860 — give points for those 3
  > Please clarify which three items you would like me to provide points for, as there is no preceding c
- **B7** [finance] ref=False cov=0.016 lat=213.3s tok=3076 — convert into tabliture
  > Please provide the musical notation, chord progression, or description of the melody you would like 
