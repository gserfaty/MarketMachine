"""Monthly precomputed forecasts: `python -m housing.precompute OUT_DIR` writes <h>m.json; apps load them via `use`."""
from __future__ import annotations

import json
import logging
import sys
import urllib.request
from pathlib import Path

from housing import data, model

log = logging.getLogger("marketmachine.precompute")
HORIZONS = (3, 12, 24)
URL = "https://raw.githubusercontent.com/gserfaty/MarketMachine/forecasts/{h}m.json"


def build(out_dir: str) -> None:
    i = data.load_forecast_inputs()
    key = model.as_of_key(i["long_df"], i["supply"], i["months_supply"])
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    for h in HORIZONS:
        res = model.train_and_evaluate(i["long_df"], i["mortgage"], supply=i["supply"], horizon=h, months_supply=i["months_supply"])
        Path(out_dir, f"{h}m.json").write_text(json.dumps({"as_of_key": key, "horizon": h, "result": model.result_to_json(res)}))


def fetch(h: int) -> str | None:
    """Raw JSON text of the published forecast, or None on any network/HTTP error."""
    try:
        with urllib.request.urlopen(URL.format(h=h), timeout=20) as r:
            return r.read().decode()
    except Exception as e:  # noqa: BLE001
        log.warning("precomputed %sm forecast unavailable (%s); training on demand", h, e)
        return None


def use(payload: str | None, key: str) -> model.ForecastResult | None:
    """The precomputed result if its as_of_key equals `key` (same data month and model code), else None."""
    try:
        d = json.loads(payload) if payload else None
        if d and d["as_of_key"] == key:
            return model.result_from_json(d["result"])
        if d:
            log.info("precomputed forecast is stale (%s != %s); training on demand", d["as_of_key"], key)
    except Exception as e:  # noqa: BLE001
        log.warning("precomputed forecast unreadable (%s); training on demand", e)
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build(sys.argv[1])
