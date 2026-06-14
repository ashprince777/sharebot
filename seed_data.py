import asyncio
from datetime import datetime, timezone, timedelta
import random
import yfinance as yf
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.models.stock import StockMetadata, StockOHLCV
from app.ml_engine.pipeline import train_and_evaluate_all


SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL", "LT", "HINDUNILVR", "ITC", 
    "BAJFINANCE", "MARUTI", "SUNPHARMA", "AXISBANK", "NTPC", "ADANIENT", "ADANIPORTS", "ADANIPOWER", "ALKEM", "AMBUJACEM", 
    "APOLLOHOSP", "ASIANPAINT", "AUROPHARMA", "DMART", "BANDHANBNK", "BANKBARODA", "BEL", "BHEL", "BIOCON", "BOSCHLTD", 
    "BPCL", "BRITANNIA", "CANBK", "CHOLAFIN", "CIPLA", "COALINDIA", "COLPAL", "CONCOR", "DLF", "EICHERMOT", 
    "GAIL", "GLAND", "GODREJCP", "GRASIM", "HAVELLS", "HEROMOTOCO", "HINDALCO", "HAL", "INDHOTEL", "IOC", 
    "IRCTC", "JSWSTEEL", "KOTAKBANK", "LICHSGFIN", "LTM", "M&M", "MARICO", "UNITDSPR", "MUTHOOTFIN", "NESTLEIND", 
    "NMDC", "ONGC", "PAGEIND", "PNB", "POWERGRID", "RECLTD", "SBILIFE", "SHREECEM", "SRF", "TATACOMM", 
    "TATACONSUM", "TATAELXSI", "TMCV", "TATAPOWER", "TATASTEEL", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "VBL", 
    "WIPRO", "YESBANK", "ZEEL", "ETERNAL", "BATAINDIA", "BERGEPAINT", "DABUR", "HINDPETRO", "IDFCFIRSTB", "INDUSINDBK", 
    "INDIGO", "JINDALSTEL", "JUBLFOOD", "LUPIN", "MRF", "OFSS", "PIRAMALFIN", "PFC", "SAIL", "TRENT",
    "JIOFIN", "IRFC", "RVNL", "NHPC", "SJVN", "IREDA", "HUDCO", "HDFCLIFE", "SBICARD", "MSTC", "HCLTECH"
]

SECTORS = {
    "Financial Services": ["HDFCBANK", "ICICIBANK", "SBIN", "BAJFINANCE", "AXISBANK", "KOTAKBANK", "PNB", "BANDHANBNK", "BANKBARODA", "CANBK", "CHOLAFIN", "LICHSGFIN", "MUTHOOTFIN", "RECLTD", "PFC", "YESBANK", "IDFCFIRSTB", "INDUSINDBK", "JIOFIN", "IRFC", "IREDA", "HUDCO", "HDFCLIFE", "SBICARD"],
    "Information Technology": ["TCS", "INFY", "TECHM", "WIPRO", "LTM", "TATAELXSI", "OFSS", "HCLTECH"],
    "Oil & Gas": ["RELIANCE", "BPCL", "ONGC", "IOC", "GAIL", "HINDPETRO"],
    "Automobile": ["MARUTI", "HEROMOTOCO", "M&M", "TMCV", "EICHERMOT"],
    "FMCG": ["HINDUNILVR", "ITC", "BRITANNIA", "COLPAL", "GODREJCP", "MARICO", "NESTLEIND", "TATACONSUM", "VBL", "DABUR"],
    "Healthcare": ["SUNPHARMA", "ALKEM", "APOLLOHOSP", "AUROPHARMA", "CIPLA", "GLAND", "LUPIN", "PIRAMALFIN"],
    "Metals & Mining": ["COALINDIA", "HINDALCO", "JSWSTEEL", "NMDC", "TATASTEEL", "JINDALSTEL", "SAIL"],
    "Power & Utilities": ["NTPC", "POWERGRID", "TATAPOWER", "ADANIPOWER", "NHPC", "SJVN"],
    "Consumer Durables": ["ASIANPAINT", "HAVELLS", "TITAN", "PAGEIND", "BATAINDIA", "BERGEPAINT"],
    "Construction & Materials": ["LT", "AMBUJACEM", "DLF", "GRASIM", "SHREECEM", "ULTRACEMCO"],
    "Services & Others": ["ADANIENT", "ADANIPORTS", "DMART", "BEL", "BHEL", "BIOCON", "BOSCHLTD", "CONCOR", "INDHOTEL", "IRCTC", "SBILIFE", "SRF", "TATACOMM", "UPL", "ZEEL", "ETERNAL", "INDIGO", "JUBLFOOD", "MRF", "TRENT", "RVNL", "MSTC"]
}

NAMES = {
    "MSTC": "MSTC Ltd.",
    "HCLTECH": "HCL Technologies Ltd.",
    "RELIANCE": "Reliance Industries Ltd.",
    "TCS": "Tata Consultancy Services Ltd.",
    "HDFCBANK": "HDFC Bank Ltd.",
    "INFY": "Infosys Ltd.",
    "ICICIBANK": "ICICI Bank Ltd.",
    "SBIN": "State Bank of India",
    "BHARTIARTL": "Bharti Airtel Ltd.",
    "LT": "Larsen & Tourbro Ltd.",
    "HINDUNILVR": "Hindustan Unilever Ltd.",
    "ITC": "ITC Ltd.",
    "BAJFINANCE": "Bajaj Finance Ltd.",
    "MARUTI": "Maruti Suzuki India Ltd.",
    "SUNPHARMA": "Sun Pharmaceutical Industries Ltd.",
    "AXISBANK": "Axis Bank Ltd.",
    "NTPC": "NTPC Ltd.",
    "ETERNAL": "Eternal Ltd. (Zomato)",
    "ZEEL": "Zee Entertainment Enterprises Ltd.",
    "WIPRO": "Wipro Ltd.",
    "TMCV": "Tata Motors Ltd.",
    "KOTAKBANK": "Kotak Mahindra Bank Ltd.",
    "ADANIENT": "Adani Enterprises Ltd.",
    "ADANIPORTS": "Adani Ports & SEZ Ltd.",
    "ASIANPAINT": "Asian Paints Ltd.",
    "COALINDIA": "Coal India Ltd.",
    "TITAN": "Titan Company Ltd.",
    "ULTRACEMCO": "UltraTech Cement Ltd.",
    "POWERGRID": "Power Grid Corporation of India Ltd.",
    "NESTLEIND": "Nestle India Ltd.",
    "JSWSTEEL": "JSW Steel Ltd.",
    "ONGC": "Oil & Natural Gas Corporation Ltd.",
    "HINDALCO": "Hindalco Industries Ltd.",
    "GRASIM": "Grasim Industries Ltd.",
    "LTM": "LTM Ltd. (LTIMindtree)",
    "TATACONSUM": "Tata Consumer Products Ltd.",
    "SBILIFE": "SBI Life Insurance Company Ltd.",
    "HAL": "Hindustan Aeronautics Ltd.",
    "EICHERMOT": "Eicher Motors Ltd.",
    "BPCL": "Bharat Petroleum Corporation Ltd.",
    "BRITANNIA": "Britannia Industries Ltd.",
    "INDUSINDBK": "IndusInd Bank Ltd.",
    "DLF": "DLF Ltd.",
    "HAVELLS": "Havells India Ltd.",
    "INDIGO": "InterGlobe Aviation Ltd. (IndiGo)",
    "CIPLA": "Cipla Ltd.",
    "APOLLOHOSP": "Apollo Hospitals Enterprise Ltd.",
    "TATASTEEL": "Tata Steel Ltd.",
    "BEL": "Bharat Electronics Ltd.",
    "PNB": "Punjab National Bank",
    "IOC": "Indian Oil Corporation Ltd.",
    "GAIL": "GAIL (India) Ltd.",
    "TATAPOWER": "Tata Power Company Ltd.",
    "TRENT": "Trent Ltd.",
    "VBL": "Varun Beverages Ltd.",
    "SRF": "SRF Ltd.",
    "RECLTD": "REC Ltd.",
    "PFC": "Power Finance Corporation Ltd.",
    "AMBUJACEM": "Ambuja Cements Ltd.",
    "SHREECEM": "Shree Cement Ltd.",
    "COLPAL": "Colgate-Palmolive (India) Ltd.",
    "DABUR": "Dabur India Ltd.",
    "MRF": "MRF Ltd.",
    "BOSCHLTD": "Bosch Ltd.",
    "HEROMOTOCO": "Hero MotoCorp Ltd.",
    "M&M": "Mahindra & Mahindra Ltd.",
    "TATACOMM": "Tata Communications Ltd.",
    "TATAELXSI": "Tata Elxsi Ltd.",
    "TECHM": "Tech Mahindra Ltd.",
    "YESBANK": "Yes Bank Ltd.",
    "BATAINDIA": "Bata India Ltd.",
    "BERGEPAINT": "Berger Paints India Ltd.",
    "BIOCON": "Biocon Ltd.",
    "HINDPETRO": "Hindustan Petroleum Corporation Ltd.",
    "IDFCFIRSTB": "IDFC First Bank Ltd.",
    "JINDALSTEL": "Jindal Steel & Power Ltd.",
    "JUBLFOOD": "Jubilant FoodWorks Ltd.",
    "LUPIN": "Lupin Ltd.",
    "OFSS": "Oracle Financial Services Software Ltd.",
    "PIRAMALFIN": "Piramal Finance Ltd.",
    "SAIL": "Steel Authority of India Ltd.",
    "ALKEM": "Alkem Laboratories Ltd.",
    "AUROPHARMA": "Aurobindo Pharma Ltd.",
    "CONCOR": "Container Corporation of India Ltd.",
    "GLAND": "Gland Pharma Ltd.",
    "GODREJCP": "Godrej Consumer Products Ltd.",
    "INDHOTEL": "The Indian Hotels Company Ltd.",
    "IRCTC": "Indian Railway Catering & Tourism Corporation Ltd.",
    "LICHSGFIN": "LIC Housing Finance Ltd.",
    "MARICO": "Marico Ltd.",
    "UNITDSPR": "United Spirits Ltd.",
    "MUTHOOTFIN": "Muthoot Finance Ltd.",
    "NMDC": "NMDC Ltd.",
    "PAGEIND": "Page Industries Ltd.",
    "CANBK": "Canara Bank",
    "CHOLAFIN": "Cholamandalam Investment & Finance Co. Ltd.",
    "BANDHANBNK": "Bandhan Bank Ltd.",
    "BANKBARODA": "Bank of Baroda",
    "ADANIPOWER": "Adani Power Ltd.",
    "BHEL": "Bharat Heavy Electricals Ltd.",
    "DMART": "Avenue Supermarts Ltd. (DMart)",
    "JIOFIN": "Jio Financial Services Ltd.",
    "IRFC": "Indian Railway Finance Corporation Ltd.",
    "RVNL": "Rail Vikas Nigam Ltd.",
    "NHPC": "NHPC Ltd.",
    "SJVN": "SJVN Ltd.",
    "IREDA": "Indian Renewable Energy Development Agency Ltd.",
    "HUDCO": "Housing & Urban Development Corporation Ltd.",
    "HDFCLIFE": "HDFC Life Insurance Co. Ltd.",
    "SBICARD": "SBI Cards & Payment Services Ltd."
}


symbol_to_sector = {}
for sector, symbols in SECTORS.items():
    for sym in symbols:
        symbol_to_sector[sym] = sector

STOCKS_TO_SEED = []
for idx, sym in enumerate(SYMBOLS):
    company_name = NAMES.get(sym, f"{sym} Ltd.")
    industry = symbol_to_sector.get(sym, "Diversified")
    isin = f"INE{idx+100:03d}A01{idx+10:02d}"
    STOCKS_TO_SEED.append({
        "symbol": sym,
        "company_name": company_name,
        "isin": isin,
        "industry": industry,
        "exchange": "NSE"
    })

US_STOCKS = [
    {"symbol": "AAPL", "company_name": "Apple Inc.", "isin": "US0378331005", "industry": "Information Technology", "exchange": "NASDAQ"},
    {"symbol": "MSFT", "company_name": "Microsoft Corporation", "isin": "US5949181045", "industry": "Information Technology", "exchange": "NASDAQ"},
    {"symbol": "TSLA", "company_name": "Tesla, Inc.", "isin": "US88160R1014", "industry": "Automobile", "exchange": "NASDAQ"},
    {"symbol": "NVDA", "company_name": "NVIDIA Corporation", "isin": "US67066G1040", "industry": "Information Technology", "exchange": "NASDAQ"},
    {"symbol": "AMZN", "company_name": "Amazon.com, Inc.", "isin": "US0231351067", "industry": "Services & Others", "exchange": "NASDAQ"},
    {"symbol": "GOOGL", "company_name": "Alphabet Inc.", "isin": "US02079K3059", "industry": "Information Technology", "exchange": "NASDAQ"},
    {"symbol": "META", "company_name": "Meta Platforms, Inc.", "isin": "US30303M1027", "industry": "Information Technology", "exchange": "NASDAQ"},
    {"symbol": "BRK-B", "company_name": "Berkshire Hathaway Inc.", "isin": "US0846707026", "industry": "Financial Services", "exchange": "NYSE"},
    {"symbol": "LLY", "company_name": "Eli Lilly and Company", "isin": "US5324571083", "industry": "Healthcare", "exchange": "NYSE"},
    {"symbol": "AVGO", "company_name": "Broadcom Inc.", "isin": "US11135F1012", "industry": "Information Technology", "exchange": "NASDAQ"},
    {"symbol": "JPM", "company_name": "JPMorgan Chase & Co.", "isin": "US46625H1005", "industry": "Financial Services", "exchange": "NYSE"},
    {"symbol": "V", "company_name": "Visa Inc.", "isin": "US92826C8394", "industry": "Financial Services", "exchange": "NYSE"},
    {"symbol": "UNH", "company_name": "UnitedHealth Group Inc.", "isin": "US91324P1021", "industry": "Healthcare", "exchange": "NYSE"},
    {"symbol": "MA", "company_name": "Mastercard Incorporated", "isin": "US57636Q1040", "industry": "Financial Services", "exchange": "NYSE"},
    {"symbol": "WMT", "company_name": "Walmart Inc.", "isin": "US9311421039", "industry": "FMCG", "exchange": "NYSE"},
    {"symbol": "XOM", "company_name": "Exxon Mobil Corporation", "isin": "US30231G1022", "industry": "Oil & Gas", "exchange": "NYSE"},
    {"symbol": "JNJ", "company_name": "Johnson & Johnson", "isin": "US4781601046", "industry": "Healthcare", "exchange": "NYSE"},
    {"symbol": "PG", "company_name": "Procter & Gamble Company", "isin": "US7427181094", "industry": "FMCG", "exchange": "NYSE"},
    {"symbol": "ORCL", "company_name": "Oracle Corporation", "isin": "US68389X1054", "industry": "Information Technology", "exchange": "NYSE"},
    {"symbol": "COST", "company_name": "Costco Wholesale Corp.", "isin": "US22160K1051", "industry": "Services & Others", "exchange": "NASDAQ"},
    {"symbol": "HD", "company_name": "Home Depot, Inc.", "isin": "US4370761029", "industry": "Services & Others", "exchange": "NYSE"},
    {"symbol": "NFLX", "company_name": "Netflix, Inc.", "isin": "US64110L1061", "industry": "Services & Others", "exchange": "NASDAQ"},
    {"symbol": "KO", "company_name": "Coca-Cola Company", "isin": "US1912161007", "industry": "FMCG", "exchange": "NYSE"},
    {"symbol": "MRK", "company_name": "Merck & Co., Inc.", "isin": "US58933Y1055", "industry": "Healthcare", "exchange": "NYSE"},
    {"symbol": "AMD", "company_name": "Advanced Micro Devices", "isin": "US0079031078", "industry": "Information Technology", "exchange": "NASDAQ"},
    {"symbol": "PEP", "company_name": "PepsiCo, Inc.", "isin": "US7134481081", "industry": "FMCG", "exchange": "NASDAQ"},
    {"symbol": "CVX", "company_name": "Chevron Corporation", "isin": "US1667641005", "industry": "Oil & Gas", "exchange": "NYSE"},
    {"symbol": "QCOM", "company_name": "Qualcomm Incorporated", "isin": "US7475251036", "industry": "Information Technology", "exchange": "NASDAQ"},
    {"symbol": "ADBE", "company_name": "Adobe Inc.", "isin": "US00724F1012", "industry": "Information Technology", "exchange": "NASDAQ"},
    {"symbol": "CRM", "company_name": "Salesforce, Inc.", "isin": "US79466L3024", "industry": "Information Technology", "exchange": "NYSE"},
    {"symbol": "BAC", "company_name": "Bank of America Corp.", "isin": "US0605051046", "industry": "Financial Services", "exchange": "NYSE"},
    {"symbol": "ACN", "company_name": "Accenture plc", "isin": "IE00B4BNMY34", "industry": "Information Technology", "exchange": "NYSE"},
    {"symbol": "AMGN", "company_name": "Amgen Inc.", "isin": "US0311621009", "industry": "Healthcare", "exchange": "NASDAQ"},
    {"symbol": "MCD", "company_name": "McDonald's Corporation", "isin": "US5801351017", "industry": "Services & Others", "exchange": "NYSE"},
    {"symbol": "INTU", "company_name": "Intuit Inc.", "isin": "US4612021034", "industry": "Information Technology", "exchange": "NASDAQ"},
    {"symbol": "CSCO", "company_name": "Cisco Systems, Inc.", "isin": "US17275R1023", "industry": "Information Technology", "exchange": "NASDAQ"},
    {"symbol": "ABT", "company_name": "Abbott Laboratories", "isin": "US0028241000", "industry": "Healthcare", "exchange": "NYSE"},
    {"symbol": "DIS", "company_name": "Walt Disney Company", "isin": "US2546871060", "industry": "Services & Others", "exchange": "NYSE"},
    {"symbol": "GE", "company_name": "General Electric Company", "isin": "US3696043013", "industry": "Power & Utilities", "exchange": "NYSE"},
    {"symbol": "INTC", "company_name": "Intel Corporation", "isin": "US4581401001", "industry": "Information Technology", "exchange": "NASDAQ"},
    {"symbol": "TXN", "company_name": "Texas Instruments Inc.", "isin": "US8825081040", "industry": "Information Technology", "exchange": "NASDAQ"},
    {"symbol": "IBM", "company_name": "International Business Machines", "isin": "US4592001014", "industry": "Information Technology", "exchange": "NYSE"},
    {"symbol": "CAT", "company_name": "Caterpillar Inc.", "isin": "US1491231015", "industry": "Construction & Materials", "exchange": "NYSE"},
    {"symbol": "MS", "company_name": "Morgan Stanley", "isin": "US6174464486", "industry": "Financial Services", "exchange": "NYSE"},
    {"symbol": "GS", "company_name": "Goldman Sachs Group", "isin": "US38141G1040", "industry": "Financial Services", "exchange": "NYSE"},
    {"symbol": "VZ", "company_name": "Verizon Communications", "isin": "US92343V1044", "industry": "Services & Others", "exchange": "NYSE"},
    {"symbol": "AMAT", "company_name": "Applied Materials, Inc.", "isin": "US0382221051", "industry": "Information Technology", "exchange": "NASDAQ"},
    {"symbol": "HON", "company_name": "Honeywell International", "isin": "US4385161063", "industry": "Construction & Materials", "exchange": "NYSE"},
    {"symbol": "RTX", "company_name": "RTX Corporation", "isin": "US78573M1045", "industry": "Services & Others", "exchange": "NYSE"},
    {"symbol": "PFE", "company_name": "Pfizer Inc.", "isin": "US7170811035", "industry": "Healthcare", "exchange": "NYSE"}
]
STOCKS_TO_SEED.extend(US_STOCKS)


async def seed_stock_metadata(session: AsyncSession):
    print("Seeding stock metadata details...")
    for item in STOCKS_TO_SEED:
        stmt = select(StockMetadata).where(StockMetadata.symbol == item["symbol"])
        res = await session.execute(stmt)
        existing = res.scalars().first()

        if not existing:
            stock = StockMetadata(
                symbol=item["symbol"],
                series="EQ",
                company_name=item["company_name"],
                isin=item["isin"],
                industry=item["industry"],
                exchange=item["exchange"],
                lot_size=1,
                is_active=True
            )
            session.add(stock)
            print(f"  Added metadata: {item['symbol']}")
    await session.commit()


async def seed_historical_candles(session: AsyncSession, count: int = 150):
    print("Fetching historical candles from Yahoo Finance in bulk...")

    tickers_to_download = []
    symbol_map = {}
    
    for item in STOCKS_TO_SEED:
        symbol = item["symbol"]
        
        # Check if candles already exist
        stmt = select(StockOHLCV).where(StockOHLCV.symbol == symbol).limit(1)
        res = await session.execute(stmt)
        if res.scalars().first():
            print(f"  Candles already exist for {symbol}. Skipping.")
            continue
            
        if item.get("exchange") in ["NASDAQ", "NYSE"]:
            ticker_ns = symbol
        else:
            ticker_ns = "MSTCLTD.NS" if symbol == "MSTC" else f"{symbol}.NS"
        tickers_to_download.append(ticker_ns)
        symbol_map[ticker_ns] = symbol

    if not tickers_to_download:
        print("  All stock candles already exist. Seeding skipped.")
        return

    print(f"  Downloading data for {len(tickers_to_download)} tickers at once...")
    data = yf.download(tickers_to_download, period="2y", interval="1d", group_by="ticker")

    for ticker_ns, symbol in symbol_map.items():
        try:
            # Handle case where download fails or returns empty for a specific ticker
            if ticker_ns not in data.columns.levels[0]:
                print(f"  ⚠️ No data found in download for {symbol}")
                continue
                
            ticker_data = data[ticker_ns].dropna(subset=["Open", "High", "Low", "Close", "Volume"])
            
            candles_to_add = []
            for timestamp, row in ticker_data.iterrows():
                if timestamp.tzinfo is not None:
                    candle_time = timestamp.tz_convert(timezone.utc).to_pydatetime()
                else:
                    candle_time = timestamp.replace(tzinfo=timezone.utc).to_pydatetime()

                candle = StockOHLCV(
                    time=candle_time,
                    symbol=symbol,
                    resolution="1d",
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                    open_interest=0
                )
                candles_to_add.append(candle)
            
            session.add_all(candles_to_add)
            print(f"  Added {len(candles_to_add)} actual daily candles for {symbol}.")
        except Exception as e:
            print(f"  ❌ Error seeding {symbol}: {str(e)}")
            
    await session.commit()


async def clear_database(session: AsyncSession):
    print("Clearing database tables...")
    await session.execute(text("TRUNCATE TABLE stock_ohlcv, stock_metadata, ml_models, model_predictions CASCADE"))
    await session.commit()


async def pretrain_ai_models():
    print("Launching AI pipeline model training...")
    async with AsyncSessionLocal() as session:
        # Load RELIANCE candles to pre-train our models
        stmt = select(StockOHLCV).where(StockOHLCV.symbol == "RELIANCE").order_by(StockOHLCV.time.asc())
        res = await session.execute(stmt)
        candles = list(res.scalars().all())

        if len(candles) < 60:
            print("[ERROR] Cannot pre-train models. Insufficient candles in database.")
            return

        try:
            metrics = train_and_evaluate_all(candles)
            print("[SUCCESS] Pre-training completed successfully!")
            print("Model Metrics:")
            print(json_metrics := {k: {mk: f"{mv:.4f}" for mk, mv in v.items()} for k, v in metrics.items()})
        except Exception as e:
            print(f"[ERROR] Pre-training failed: {str(e)}")


async def seed_admin_user(session: AsyncSession):
    print("Seeding admin user...")
    from app.models.user import User
    from app.core.security import get_password_hash
    
    # Check if admin already exists
    stmt = select(User).where(User.email == "admin@sharebot.com")
    res = await session.execute(stmt)
    admin = res.scalars().first()
    
    if not admin:
        admin = User(
            email="admin@sharebot.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Administrator",
            is_active=True,
            is_verified=True,
            role="admin"
        )
        session.add(admin)
        print("  Created admin@sharebot.com user.")
    else:
        print("  admin@sharebot.com user already exists.")
    await session.commit()


async def main():
    print("Starting database seeding process...")
    async with AsyncSessionLocal() as session:
        # Check if we already have stocks metadata seeded
        stmt = select(StockMetadata).limit(1)
        res = await session.execute(stmt)
        has_data = res.scalars().first() is not None
        
        if has_data:
            print("Database already contains stock metadata. Skipping metadata seeding.")
        else:
            await clear_database(session)
            await seed_admin_user(session)
            await seed_stock_metadata(session)
            
        # Check if we have candle data
        stmt_candles = select(StockOHLCV).limit(1)
        res_candles = await session.execute(stmt_candles)
        has_candles = res_candles.scalars().first() is not None
        
        if not has_candles:
            await seed_historical_candles(session, count=500)
        else:
            print("Database already contains historical candles. Skipping candle downloading.")
            
        # Always make sure the admin user exists
        await seed_admin_user(session)
        
    # Always try to train models on startup to populate saved_models/ in container memory
    try:
        await pretrain_ai_models()
    except Exception as e:
        print(f"Warning: model pretraining failed/skipped: {e}")
        
    print("Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
