# DOURMOUSE shell — commercial hub drop-in

Files drop into a dourmouse checkout: `hub.html` → `ui/`, `serve_hub.py` →
`tools/`, `index.html` → `ui/` (overwrites — adds the COMMERCIAL HUB button).

Architecture (user-mandated): **dourmouse is the shell**; ATLAS (backtest
engine + full data registry) and the TAILSCALE FEED (live agent chat) live
inside it as separate large-scale UIs, one per tab.

## Run
    python tools/serve_hub.py --port 8791   # serves ui/ incl. hub.html
    open http://127.0.0.1:8791/hub.html

Dependencies (both running on the desktop):
    ATLAS  -> http://127.0.0.1:8790  (scripts/engine_api.py)
    FEED   -> http://127.0.0.1:8788  (relay/chat_feed.py)

Tabs: ATLAS (key coverage, run backtests, data inspector) · DOURMOUSE
(core dispatch UI) · TAILSCALE FEED (live relay chat, send box included).
