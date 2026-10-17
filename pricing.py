import yfinance as yf
from datetime import datetime, timedelta
import time
import threading

# Global cache for Nifty 50 historical dataframe and precalculated returns
_nifty_hist = None
_nifty_cmp = None
_nifty_cache = {}

def init_nifty():
    global _nifty_hist, _nifty_cmp
    if _nifty_hist is not None:
        return
    try:
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(start="2020-01-01")
        hist = hist.dropna(subset=["Close"])
        if not hist.empty:
            _nifty_hist = hist
            try:
                live = nifty.fast_info.last_price
                _nifty_cmp = float(live) if (live and live > 0) else float(hist.iloc[-1]["Close"])
            except Exception:
                _nifty_cmp = float(hist.iloc[-1]["Close"])
    except Exception as e:
        print(f"Warning initializing Nifty benchmark: {e}")

def get_live_price(ticker_obj, hist):
    """Get the live/latest price using fast_info or last history close."""
    try:
        live = ticker_obj.fast_info.last_price
        if live and live > 0:
            return float(live)
    except Exception:
        pass
    if not hist.empty:
        return float(hist.iloc[-1]["Close"])
    return None

def fetch_nifty_return(video_date: str) -> float:
    """Fetch Nifty 50 (^NSEI) return from video date to present (instant in-memory lookup)."""
    if video_date in _nifty_cache:
        return _nifty_cache[video_date]

    init_nifty()
    if _nifty_hist is None or _nifty_hist.empty or _nifty_cmp is None:
        _nifty_cache[video_date] = 0.0
        return 0.0

    try:
        sub = _nifty_hist[_nifty_hist.index >= video_date]
        if sub.empty:
            _nifty_cache[video_date] = 0.0
            return 0.0
        nifty_start = float(sub.iloc[0]["Close"])
        nifty_return = round(((_nifty_cmp - nifty_start) / nifty_start) * 100, 2)
        _nifty_cache[video_date] = nifty_return
        return nifty_return
    except Exception:
        _nifty_cache[video_date] = 0.0
        return 0.0

def fetch_stock_prices(ticker: str, video_date: str) -> dict:
    """Queries yfinance for the closing price on video date and live price/alpha."""
    if not ticker or ticker == 'N/A':
        return None

    result_container = [None]
    exception_container = [None]

    def _fetch():
        try:
            start_dt = datetime.strptime(video_date, "%Y-%m-%d")
            ticker_obj = yf.Ticker(ticker)

            hist = ticker_obj.history(start=start_dt.strftime("%Y-%m-%d"))
            hist = hist.dropna(subset=["Close"])

            if hist.empty:
                time.sleep(0.5)
                hist = ticker_obj.history(start=start_dt.strftime("%Y-%m-%d"))
                hist = hist.dropna(subset=["Close"])

            current_price = get_live_price(ticker_obj, hist)

            if hist.empty:
                if current_price is None:
                    return
                start_price = current_price
                change_pct = 0.0
            else:
                start_price = float(hist.iloc[0]["Close"])
                if current_price is None:
                    current_price = float(hist.iloc[-1]["Close"])
                change_pct = ((current_price - start_price) / start_price) * 100

            nifty_return = fetch_nifty_return(video_date)
            alpha = round(change_pct - nifty_return, 2)

            result_container[0] = {
                "start_price": round(start_price, 2),
                "current_price": round(current_price, 2),
                "change": f"{change_pct:+.2f}%",
                "change_pct": round(change_pct, 2),
                "nifty_return": f"{nifty_return:+.2f}%",
                "nifty_return_pct": nifty_return,
                "alpha": f"{alpha:+.2f}%",
                "alpha_pct": alpha
            }
        except Exception as e:
            exception_container[0] = e

    t = threading.Thread(target=_fetch, daemon=True)
    t.start()
    t.join(timeout=8)

    if t.is_alive() or exception_container[0]:
        return None

    return result_container[0]
