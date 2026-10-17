import os
import csv
import urllib.request
import difflib
import re

# Local caching configuration
CSV_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
CSV_FILENAME = "EQUITY_L.csv"

# Pre-defined mappings for common abbreviations/spoken names to NSE symbols
COMMON_MAPPINGS = {
    # Major banks
    "sbi": "SBIN",
    "state bank of india": "SBIN",
    "hdfc": "HDFCBANK",
    "hdfc bank": "HDFCBANK",
    "icici": "ICICIBANK",
    "icici bank": "ICICIBANK",
    "kotak": "KOTAKBANK",
    "kotak mahindra": "KOTAKBANK",
    "kotak mahindra bank": "KOTAKBANK",
    "axis": "AXISBANK",
    "axis bank": "AXISBANK",
    # Major conglomerates
    "reliance": "RELIANCE",
    "reliance industries": "RELIANCE",
    "l&t": "LT",
    "l and t": "LT",
    "larsen and toubro": "LT",
    "larsen & toubro": "LT",
    "m&m": "M&M",
    "mahindra & mahindra": "M&M",
    "mahindra and mahindra": "M&M",
    # IT companies
    "tcs": "TCS",
    "tata consultancy": "TCS",
    "tata consultancy services": "TCS",
    "infy": "INFY",
    "infosys": "INFY",
    "wipro": "WIPRO",
    # FMCG / Consumer
    "itc": "ITC",
    "hindustan unilever": "HINDUNILVR",
    "hul": "HINDUNILVR",
    # Sunday Show frequently mentioned stocks (fuzzy matcher can't resolve)
    "finotex chemical": "FCL",
    "fineotex chemical": "FCL",
    "fineotex": "FCL",
    "finotex": "FCL",
    "pn gadgil": "PNGJL",
    "p n gadgil": "PNGJL",
    "pn gadgil jewellers": "PNGJL",
    "deccan gold": "DECNGOLD",
    "deccan gold mines": "DECNGOLD",
    "novartis india": "NOVARTIND",
    "novartis": "NOVARTIND",
    "astra microwave": "ASTRAMICRO",
    "bajaj finserv": "BAJAJFINSV",
    "bajaj finance": "BAJFINANCE",
    "home first finance": "HOMEFIRST",
    "home first": "HOMEFIRST",
    "india shelter": "INDIASHLTR",
    "india shelter housing finance": "INDIASHLTR",
    "india shelter housing": "INDIASHLTR",
    "black box": "BBOX",
    "anant raj": "ANANTRAJ",
    "raymond realty": "RAYMONDREL",
    "raymond": "RAYMOND",
    "latent view": "LATENTVIEW",
    "latent view analytics": "LATENTVIEW",
    "tata motors": "TATAMOTORS",
    "bharti airtel": "BHARTIARTL",
    "airtel": "BHARTIARTL",
    "maruti suzuki": "MARUTI",
    "maruti": "MARUTI",
    "sun pharma": "SUNPHARMA",
    "sun pharmaceutical": "SUNPHARMA",
    "titan": "TITAN",
    "titan company": "TITAN",
    "ultratech cement": "ULTRACEMCO",
    "ultratech": "ULTRACEMCO",
    "godavari power": "GPIL",
    "godavari power and ispat": "GPIL",
    "steel exchange": "STEELXIND",
    "steel exchange india": "STEELXIND",
    "jaiswal neco": "JAYNECOIND",
    "jaiswal neco industries": "JAYNECOIND",
    "jayaswal neco": "JAYNECOIND",
    # Pranjal Kamra frequently analyzed entities
    "sreeleathers": "SREEL",
    "sree leathers": "SREEL",
    "dmart": "DMART",
    "d-mart": "DMART",
    "avenue supermarts": "DMART",
    "tata consumer": "TATACONSUM",
    "tata consumer products": "TATACONSUM",
    "tata salt": "TATACONSUM",
    "yes bank": "YESBANK",
    "cdsl": "CDSL",
    "bse": "BSE",
    "bse ltd": "BSE",
    "bse ltd.": "BSE",
    "bombay stock exchange": "BSE",
    "bombay stock exchange (bse)": "BSE",
    "narayana health": "NH",
    "narayana hrudayalaya": "NH",
    "johnson controls-hitachi air conditioning india": "JCHAC",
    "max life insurance": "MFSL",
    "mcx": "MCX",
    "multi commodity exchange": "MCX",
    "cams": "CAMS",
    "kfintech": "KFINTECH",
    "kfin technologies": "KFINTECH",
    "indigo": "INDIGO",
    "interglobe aviation": "INDIGO",
    "zomato": "ZOMATO",
    "swiggy": "SWIGGY",
    "paytm": "PAYTM",
    "nykaa": "NYKAA",
    "policybazaar": "POLICYBZR",
    "pb fintech": "POLICYBZR",
    "pidilite": "PIDILITIND",
    "asian paints": "ASIANPAINT",
    "angel one": "ANGELONE",
    "irctc": "IRCTC",
    "indian railway catering": "IRCTC",
    "central depository services (india) ltd.": "CDSL",
    "central depository services": "CDSL",
    "multi commodity exchange of india ltd.": "MCX",
    "edelweiss financial services": "EDELWEISS",
    "edelweiss": "EDELWEISS",
    "rajesh exports": "RAJESHEXPO",
    "nippon india asset management": "NAM-INDIA",
    "nam india": "NAM-INDIA",
    "mrf": "MRF",
    "vodafone idea": "IDEA",
    "ola electric mobility": "OLAELEC",
    "ola electric": "OLAELEC",
    "eicher motors": "EICHERMOT",
    "tvs motor company": "TVSMOTOR",
    "tvs motor": "TVSMOTOR",
    "wonderla holidays": "WONDERLA",
    "wonderla": "WONDERLA",
    "colgate-palmolive": "COLPAL",
    "colgate-palmolive (india)": "COLPAL",
    "barbeque nation": "BARBEQUE",
    "barbeque nation hospitality": "BARBEQUE",
    "spicejet": "SPICEJET",
    "zee news": "ZEEMEDIA",
    "zee entertainment": "ZEEL",
    "lic": "LICI",
    "life insurance corporation": "LICI",
    "life insurance corporation of india": "LICI",
    "go first": None,
    "kingfisher airlines": None,
    "akasa air": None,
    "air india": None,
    "barista": None,
    "groww": None,
    "zerodha": None,
    "meta": "META",
    "meta platforms": "META",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "apple": "AAPL",
    "microsoft": "MSFT",
    "nvidia": "NVDA",
    "tesla": "TSLA",
    "servicenow": "NOW",
    "oracle": "ORCL",
    "adobe": "ADBE",
    "netflix": "NFLX",
    "salesforce": "CRM",
    "walmart": "WMT",
    "flipkart": None,
    "acko": None,
    "chennai super kings": None,
    "parag parikh flexi cap fund": None,
    "colgate": "COLPAL",
    "godrej industries": "GODREJIND",
    "imagicaa": "IMAGICAA",
    "imagicaaworld entertainment": "IMAGICAA",
}

US_TICKERS = {
    "META", "GOOGL", "AMZN", "AAPL", "MSFT", "NVDA", "TSLA", "NOW", "ORCL", "ADBE", "CRM", "NFLX", "WMT"
}

def download_ticker_list():
    """Downloads the official NSE equity list and caches it locally."""
    # Determine the directory of the current script to cache locally
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(script_dir, CSV_FILENAME)

    if os.path.exists(local_path):
        return local_path

    print(f"Downloading NSE securities list from {CSV_URL}...")
    req = urllib.request.Request(
        CSV_URL, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            content = response.read()
            with open(local_path, "wb") as f:
                f.write(content)
        print(f"Securities list cached successfully at: {local_path}")
        return local_path
    except Exception as e:
        print(f"Warning: Failed to download official NSE securities list: {e}")
        # If download fails, check if we have a local copy anyway, or raise
        if os.path.exists(local_path):
            return local_path
        raise RuntimeError("NSE securities list is not available and download failed.")

def load_tickers():
    """Loads symbols and company names from the cached CSV."""
    local_path = download_ticker_list()
    tickers = []
    
    try:
        with open(local_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Handle potential BOM or whitespace in keys
                cleaned_row = {k.strip(): v.strip() for k, v in row.items() if k is not None}
                symbol = cleaned_row.get("SYMBOL")
                company_name = cleaned_row.get("NAME OF COMPANY")
                if symbol and company_name:
                    tickers.append((symbol, company_name))
    except Exception as e:
        print(f"Error loading tickers from CSV: {e}")
        
    return tickers

def clean_text(text: str) -> str:
    """Standardizes text by converting to lowercase and removing noise words/symbols."""
    text = text.lower()
    # Remove common corporate suffixes
    text = re.sub(r'\blimited\b|\bltd\b|\bcorp\b|\bcorporation\b', '', text)
    # Remove non-alphanumeric chars except space and '&'
    text = re.sub(r'[^a-z0-9\s&]', ' ', text)
    return " ".join(text.split())

def resolve_nse_ticker(company: str) -> str:
    """Maps a company spoken name or entity name to a strict NSE .NS ticker.
    
    Uses common mappings, exact matching, word overlap, and SequenceMatcher.
    
    Args:
        company: Spoken or written name of the company.
        
    Returns:
        The strict yfinance NSE ticker symbol (e.g. 'ASTRAMICRO.NS'), or None if unresolved.
    """
    if not company:
        return None
        
    # Check common mappings first
    query_norm = company.lower().strip()
    if query_norm in COMMON_MAPPINGS:
        mapped = COMMON_MAPPINGS[query_norm]
        if not mapped:
            return None
        return mapped if mapped in US_TICKERS else mapped + ".NS"

    tickers = load_tickers()
    query_clean = clean_text(company)
    query_words = set(query_clean.split())
    
    if not query_clean:
        return None

    # 1. Exact match on Symbol
    for symbol, name in tickers:
        if company.upper().strip() == symbol:
            return symbol + ".NS"

    # 2. Exact match on cleaned company name
    for symbol, name in tickers:
        if clean_text(name) == query_clean:
            return symbol + ".NS"

    # 3. Fuzzy matching candidates
    candidates = []
    for symbol, name in tickers:
        name_clean = clean_text(name)
        name_words = set(name_clean.split())
        
        # Word overlap score
        intersection = query_words.intersection(name_words)
        if not intersection:
            overlap_score = 0.0
        else:
            overlap_score = len(intersection) / len(query_words)
            
        # SequenceMatcher score on cleaned names
        seq_score = difflib.SequenceMatcher(None, query_clean, name_clean).ratio()
        
        # Symbol similarity score
        symbol_clean = symbol.lower()
        symbol_seq_score = difflib.SequenceMatcher(None, query_clean, symbol_clean).ratio()
        
        # Substring containment bonus
        sub_bonus = 0.0
        if query_clean in name_clean:
            sub_bonus = 0.3
            if name_clean.startswith(query_clean):
                sub_bonus = 0.5
                
        # Calculate combined score
        if query_words.issubset(name_words):
            total_score = 0.8 + 0.2 * seq_score
        else:
            total_score = 0.4 * overlap_score + 0.3 * seq_score + 0.3 * symbol_seq_score + sub_bonus
            
        candidates.append((symbol, name, total_score))
        
    candidates.sort(key=lambda x: x[2], reverse=True)
    
    # 0.60 threshold to prevent false positives (e.g. "Veranium Cloud" 0.58 != "Magellanic Cloud")
    if candidates and candidates[0][2] > 0.60:
        return candidates[0][0] + ".NS"
        
    return None

if __name__ == "__main__":
    # Test cases to verify implementation
    test_companies = ["Astra Microwave", "Reliance", "SBI", "L&T", "Tata Consultancy Services"]
    print("Testing Ticker Resolution:")
    for comp in test_companies:
        ticker = resolve_nse_ticker(comp)
        print(f"  '{comp}' -> {ticker}")
