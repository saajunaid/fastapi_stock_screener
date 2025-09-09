# your_logic/indicator_calculator.py
import pandas as pd
import pandas_ta as ta
import numpy as np
import logging
from your_logic.pattern_calculator import calculate_patterns
from your_logic.divergence_calculator import find_divergence

def calculate_vwma(high, low, close, volume, length):
    """Calculates Volume Weighted Moving Average robustly."""
    length = max(1, int(length))
    if len(close) < length:
        return pd.Series(np.nan, index=close.index)
    pv = (high + low + close) / 3 * volume
    vwma = pv.rolling(window=length).sum() / volume.rolling(window=length).sum()
    return vwma

def calculate_all_indicators(df, config, timeframe, profile):
    """Calculates all indicators based on the provided configuration."""
    logging.info(f"Calculating indicators for {timeframe}...")
    default_cfg = config['defaults']
    available_data = len(df)
    
    # --- Get Timeframe-Specific Indicator Periods ---
    vwma_periods = default_cfg['indicators']['vwma_period_by_tf'].get(timeframe, {})
    slow_vwma_period = vwma_periods.get('slow', default_cfg['indicators']['vwma_slow_period_default'])
    fast_vwma_period = vwma_periods.get('fast', default_cfg['indicators']['vwma_fast_period_default'])
    volume_lookback = default_cfg['indicators'].get('volume_lookback_period', 20)

    # --- Dynamically Adjust Periods Based on Available Data ---
    adjusted_slow_vwma = min(slow_vwma_period, available_data)
    adjusted_fast_vwma = min(fast_vwma_period, available_data)
    adjusted_volume_lookback = min(volume_lookback, available_data)
    
    # --- Calculate Base Indicators ---
    df['vwma_slow'] = calculate_vwma(df['high'], df['low'], df['close'], df['volume'], adjusted_slow_vwma)
    df['vwma_fast'] = calculate_vwma(df['high'], df['low'], df['close'], df['volume'], adjusted_fast_vwma)
    df['avg_volume'] = df['volume'].rolling(window=adjusted_volume_lookback).mean()
    
    stoch_params_base = default_cfg['stoch_rsi_params']
    stoch_params_tf = stoch_params_base.get(timeframe, stoch_params_base['1d'])
    stoch_params = stoch_params_base.get(stoch_params_tf.get('inherit'), stoch_params_tf)
    
    required_stoch_len = stoch_params.get('rsi', 14) + stoch_params.get('stoch', 14)
    if available_data > required_stoch_len:
        df.ta.stochrsi(append=True, **stoch_params)

    bbl_std = default_cfg['indicators'].get('buy_bb_stddev', 2.0)
    bbu_std = default_cfg['indicators'].get('sell_bb_stddev', 2.0)
    
    if 'vwma_slow' in df.columns and not df['vwma_slow'].dropna().empty:
        bbands_buy = ta.bbands(close=df['vwma_slow'].dropna(), length=adjusted_slow_vwma, std=bbl_std)
        bbands_sell = ta.bbands(close=df['vwma_slow'].dropna(), length=adjusted_slow_vwma, std=bbu_std)
        if bbands_buy is not None and not bbands_buy.empty:
            df['lower_bb'] = bbands_buy.iloc[:, 0]
            df['middle_bb'] = bbands_buy.iloc[:, 1]
        if bbands_sell is not None and not bbands_sell.empty:
            df['upper_bb'] = bbands_sell.iloc[:, 2]

    atr_period = default_cfg['risk_management']['atr_period']
    if available_data > atr_period:
        df.ta.atr(length=min(atr_period, available_data - 1), append=True)

    # --- Clean up and rename columns ---
    rename_map = {
        next((c for c in df.columns if c.startswith('STOCHRSIk')), None): 'stoch_k',
        next((c for c in df.columns if c.startswith('STOCHRSId')), None): 'stoch_d',
        next((c for c in df.columns if c.startswith('ATRr_')), None): 'atr',
    }
    df.rename(columns={k: v for k, v in rename_map.items() if k}, inplace=True)
    df.drop(columns=[c for c in df.columns if c.startswith(('BBM_', 'BBB_', 'BBP_'))], inplace=True, errors='ignore')

    # --- Calculate Patterns & Divergence ---
    df = calculate_patterns(df, default_cfg['pattern_sets'])
    div_cfg = default_cfg.get('divergence', {})
    df = find_divergence(df, div_cfg)
    
    # --- Final check for necessary columns ---
    required_cols = ['lower_bb', 'upper_bb', 'middle_bb', 'stoch_k', 'stoch_d', 'atr', 'vwma_slow', 'vwma_fast', 'avg_volume', 'bullish_divergence']
    for col in required_cols:
        if col not in df.columns:
            df[col] = np.nan
            
    df.dropna(subset=['close', 'open', 'high', 'low', 'volume'], inplace=True)
    
    logging.info(f"Indicators calculated for {timeframe}.")
    return df
