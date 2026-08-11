# Track B — Literature Search: Report
Date: 2026-08-11 · Campaign: Multi-Track Edge Search

## Sources searched
SSRN (site:ssrn.com via search), general web, CME group publications, NBER-adjacent
working papers surfaced via search. arXiv q-fin: not separately searched (the family
candidates it would surface — trend, momentum, ML-based — all overlap the graveyard;
noted as a scope decision).

## Queries used
1. "hedging pressure theory commodity futures returns empirical test SSRN normal backwardation"
2. "commodity index roll returns Goldman roll effect empirical study forced flows"
3. "first notice day delivery month effect commodity futures abnormal returns empirical"
4. "pre-hedging dealer order flow commodity futures predictable returns SSRN"
5. "commodity futures news under-reaction inventory surprise returns empirical study"

## Papers reviewed (6.3 extraction)

| Paper | Claimed effect | Mechanism | Graveyard overlap | Data feasibility | Eligible? |
|---|---|---|---|---|---|
| Kang et al. / "Hedging Pressure and Returns in Futures" (Fernandez-Perez et al.) | Hedging pressure (commercial net positions) predicts futures returns | Producers forced to hedge (Keynes/Hicks) | **YES — COT positioning standalone is dead** (hedging pressure IS a COT-based signal) | COT data needs assembly | NO |
| Gorton & Rouwenhorst / Hong & Yogo "Fundamentals of Commodity Futures Returns" | Rejects Keynesian hedging-pressure; fundamentals/inventory drive returns | Inventory/economic fundamentals | — | Inventory data not on drive | NO (mixed evidence, no clean free data) |
| Mou / "Limits to Arbitrage... Front-Running the Goldman Roll" | Price impact around GSCI roll dates; front-runnable | **Index funds must roll on fixed dates (structural)** | Not in graveyard, but… | Needs per-contract data (drive has continuous only); effect **documented ~80% decayed** (Irwin-Sanders-Yan 2022: average order-flow costs down >80% since 2010) | NO — decayed + data-blocked |
| Irwin, Sanders & Yan (AEPP 2022) | Index roll order-flow costs fell >80% | liquidity supply growth | — | — | NO (effect gone) |
| Bahloul (2018) "Macro news surprises and commodities" | Mixed/weak evidence surprises → commodity returns | — | Overlaps tested family (USD → gold/silver/NG killed in news_ext_campaign) | — | NO |
| Borgards (2021) "Price overreactions in commodity futures" | Intraday overreaction | — | Intraday data not on drive | Data-blocked | NO |
| "Short-Term Basis Reversal" (SSRN 2026) | Basis reversal predicts returns | Term-structure | — | Needs per-contract basis data | NO (data-blocked) |
| MacroSynergy "Economic surprises and commodity returns" | Global surprise index → industrial metals basket | — | Overlaps tested family | Surprise index is proprietary | NO |
| Pre-hedging (SSRN/INFORMS) | Dealer pre-hedging theory | — | Theoretical, no exploitable free-data signal | — | NO |

## Candidates promoted to testing
**Zero.** Every mechanism found either (a) overlaps the confirmed graveyard (hedging
pressure = COT), (b) requires per-contract/term-structure/intraday data not present on
the drive (roll front-running, basis reversal, overreaction), or (c) is documented as
decayed/arbitraged away (Goldman roll order-flow costs down >80% since 2010) — or is a
family already tested and killed in this programme (macro news → commodities).

## Honest conclusion
The literature offers no candidate that both survives the eligibility filter AND is
testable with the drive's data. The most interesting mechanism — commodity index
roll front-running — is a real forced-flow story but the modern literature
(Irwin-Sanders-Yan, CFTC studies) shows it has been arbitraged away since
financialization matured, and capturing any residual would require per-contract
futures execution we cannot do on T212 CFDs.
