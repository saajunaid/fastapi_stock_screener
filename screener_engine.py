import pandas as pd
from datetime import datetime, timedelta
import logging
import asyncio
from your_logic.config_loader import load_config
from your_logic.data_fetcher import fetch_data
from your_logic.indicator_calculator import calculate_all_indicators
from your_logic.signal_generator import generate_signals

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_sl_tp(row, strategy_cfg, risk_cfg, timeframe):
    """Calculates Stop Loss and Take Profit based on the strategy."""
    entry_price = row['close']
    current_atr = row['atr']

    if pd.isna(current_atr) or current_atr == 0:
        return None, None

    if 'stop_loss_atr_multiple' in strategy_cfg:
        sl_atr_multiple = strategy_cfg.get('stop_loss_atr_multiple', 1.5)
        tp_atr_multiple = strategy_cfg.get('take_profit_atr_multiple', 3.0)
        sl_price = entry_price - (current_atr * sl_atr_multiple)
        tp_price = entry_price + (current_atr * tp_atr_multiple)
    else:
        sl_atr_multiple = risk_cfg.get('stop_loss', {}).get('atr_multiple_by_tf', {}).get(timeframe, 2.0)
        sl_price = entry_price - (current_atr * sl_atr_multiple)
        tp_price = row.get('middle_bb')

    return sl_price, tp_price

async def run_screener_instance(api, symbol_config, update_progress_callback=None):
    """Runs a single, full market scan instance with progress reporting."""
    logging.info("Starting a new screener run...")
    config = load_config('your_logic/stock_signals_v1.yml')
    if not config:
        return []

    timeframes_to_scan = config['defaults']['timeframes_to_test']
    all_results = []
    total_symbols = len(symbol_config)
    processed_count = 0

    for symbol, profile in symbol_config.items():
        try:
            # Fetch and process data for the symbol
            all_tf_data = {}
            for tf in timeframes_to_scan:
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                end_date = datetime.now().strftime('%Y-%m-%d')
                data = await fetch_data(api, symbol, start_date, end_date, interval=tf)
                if data is not None and not data.empty:
                    all_tf_data[tf] = data
            
            for timeframe in timeframes_to_scan:
                if timeframe not in all_tf_data: continue
                
                df_with_indicators = calculate_all_indicators(all_tf_data[timeframe].copy(), config, timeframe, profile)
                data_for_signal_gen = {tf: df_with_indicators for tf in [timeframe]}
                df_with_signals = generate_signals(data_for_signal_gen, config, timeframe, profile)
                latest_candle = df_with_signals.iloc[-1]
                
                if "Buy" in latest_candle['signal']:
                    strategy_name = config['asset_profiles'][profile][timeframe]['strategy']
                    strategy_cfg = config['defaults']['strategies'][strategy_name]
                    risk_cfg = config['defaults']['risk_management']
                    sl, tp = calculate_sl_tp(latest_candle, strategy_cfg, risk_cfg, timeframe)
                    all_results.append({
                        "Symbol": symbol, "TF": timeframe, "Price": f"{latest_candle['close']:.2f}",
                        "Volume": f"{latest_candle['volume']:.0f}", "VWMA": f"{latest_candle.get('vwma_slow', 0):.2f}",
                        "Stoch_k": f"{latest_candle.get('stoch_k', 0):.2f}", "Stoch_d": f"{latest_candle.get('stoch_d', 0):.2f}",
                        "Signal": latest_candle['signal'], "Candle": "Pattern", "SL": f"{sl:.2f}" if sl else "N/A",
                        "TP": f"{tp:.2f}" if tp else "N/A", "Profile": profile
                    })
        except Exception as e:
            logging.error(f"Error processing symbol {symbol}: {e}")
        
        processed_count += 1
        if update_progress_callback:
            progress = (processed_count / total_symbols) * 100
            await update_progress_callback(progress, f"Scanning {symbol}...")

    logging.info(f"Screener run finished. Found {len(all_results)} signals.")
    return all_results
