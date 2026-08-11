# IBKR paper connector — bring it up (C8 / T6)

The desktop built the IBKR paper connector (`scripts/ibkr_connector.py`): a
place → fill → ledger round trip against the **IBKR paper account** via
`ib_insync`. Everything on the code side is done and pushed. The only thing
blocking the first real paper fill is a **human step**: an IBKR Gateway/TWS
instance must be running on this Mac, logged into the **paper** account, with
the API enabled on port **7497**.

## Why it's blocked on a human
The connector dials the Mac's own Gateway. That Gateway is a GUI application
that must be **downloaded, installed, and logged in** with the IBKR paper
account credentials. No script can (or should) do that login for you.

## What the connector needs (already prepared on this Mac)
- `ib_insync` 0.9.86 — installed in the dourmouse venv. ✓
- `dourmouse/.env` — `IBKR_HOST=127.0.0.1`, `IBKR_PORT=7497`,
  `IBKR_CLIENT_ID=17` added. ✓
- The desktop reaches this Mac at `192.168.1.95:7497` (LAN) or
  `100.84.156.49:7497` (Tailscale).

## Human steps (one-time)
1. **Install IBKR Gateway** (not TWS — Gateway is lighter) from
   <https://www.interactivebrokers.com/en/trading/ibkr-api.php> (macOS
   download). Or use TWS if you already have it.
2. **Launch it and log in** with the account set to **Paper Trading** (there's
   a "Paper" / "Live" toggle at login; choose Paper). You need a paper
   account (free, created from the client portal).
3. **Enable the API**: Gateway → Configure → API → Settings → check
   "Enable ActiveX and Socket Clients", set the **Socket port to 7497**.
4. **Trusted IPs** (important for the desktop to connect): the desktop dials
   `192.168.1.95` / `100.84.156.49`. Add both to the API "Trusted IPs" list.
   For a purely local run, `127.0.0.1` suffices.
5. **macOS firewall**: allow incoming connections for the Gateway (or the
   desktop can't reach it). If you don't want to open the LAN port, the
   desktop can dial the Tailscale IP instead.
6. Confirm it's listening: `lsof -iTCP:7497 -sTCP:LISTEN -P -n` should show
   the Gateway process.

## Verify + first paper fill
```bash
# 1. connectivity + account check (no order placed)
"/Volumes/ATLAS /dourmouse-4.0.0/.venv/bin/python" scripts/ibkr_connector.py --check

# 2. first real paper fill (EUR.USD cash, 1000 units)
"/Volumes/ATLAS /dourmouse-4.0.0/.venv/bin/python" scripts/ibkr_connector.py \
    --symbol EUR --sec-type CASH --currency USD --action BUY --qty 1000 --strategy drift_k1

# 3. ledger lands in <ATLAS_DATA>/market-data/executions/executions.csv
```

Once step 1 prints a connected account summary, tell the desktop ("Gateway is
up — run the first paper fill") and it will drive the end-to-end cycle, which
is the last unmet item in the commercial spec's definition of DONE (§4 #2).

## Honest limits
- Paper fills are instant market fills from IBKR's paper engine — realistic
  price, no slippage/queueing.
- `IBKR_CLIENT_ID` must not collide with another open TWS/Gateway connection.
- The forward-ledger column style is preserved so paper trades line up with
  the existing USDJPY drift ledger.
