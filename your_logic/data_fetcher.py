# your_logic/data_fetcher.py
import pandas as pd
import asyncio
from alpaca_trade_api.rest import APIError, TimeFrame
import logging

async def fetch_data(api, symbol, start_date, end_date, interval="1d"):
    """
    Fetches historical OHLCV data from Alpaca with robust retry logic and 
    corrected timeframe handling to match API expectations using string representation.
    """
    retries = 5
    delay = 2

    # --- Use string-based timeframe mapping for robustness ---
    timeframe_str_map = {
        "1m": "1Min", "5m": "5Min", "15m": "15Min",
        "1h": "1Hour", "4h": "4Hour",
        "1d": "1Day",
        "1w": "1Week"
    }

    timeframe_for_api = timeframe_str_map.get(interval)
    if not timeframe_for_api:
        logging.error(f"Unsupported interval provided: {interval}")
        return None

    request_args = {
        "timeframe": timeframe_for_api,
        "start": start_date,
        "end": end_date,
        "adjustment": "raw",
        "feed": "iex"
    }
    
    logging.info(f"Fetching {interval} data for {symbol} from {start_date} to {end_date}...")

    for i in range(retries):
        try:
            bars_df = api.get_bars(symbol, **request_args).df
            if bars_df.empty:
                logging.warning(f"No data returned for {symbol} on {interval}.")
                break
            
            bars_df.index = bars_df.index.tz_convert('UTC')
            bars_df = bars_df[~bars_df.index.duplicated(keep='first')]
            bars_df.sort_index(inplace=True)
            
            logging.info(f"Successfully fetched {len(bars_df)} data points for {symbol} on {interval}.")
            return bars_df

        except APIError as e:
            logging.warning(f"Alpaca API error for {symbol} on {interval}: {e}. Retrying... ({i+1}/{retries})")
            await asyncio.sleep(delay)
            delay *= 2
        except Exception as e:
            logging.warning(f"Network error for {symbol} on {interval}: {e}. Retrying... ({i+1}/{retries})")
            await asyncio.sleep(delay)
            delay *= 2

    logging.error(f"Failed to fetch data for {symbol} on {interval} after {retries} retries.")
    return None
