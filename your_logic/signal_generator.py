# your_logic/signal_generator.py
import pandas as pd
import logging

def generate_signals(all_tf_data, config, timeframe, profile, market_regime_df=None):
    """
    Generates trading signals based on the strategy defined for the given
    symbol's profile and timeframe in the configuration file.
    """
    df = all_tf_data[timeframe].copy()
    
    # --- 1. Get Strategy for the current Profile and Timeframe ---
    try:
        profile_cfg = config['asset_profiles'][profile][timeframe]
        strategy_name = profile_cfg['strategy']
        strategy_cfg = config['defaults']['strategies'][strategy_name]
        logging.info(f"Generating signals for {timeframe} using profile '{profile}' and strategy '{strategy_name}'...")
    except KeyError:
        logging.error(f"Strategy not defined for profile '{profile}' on timeframe '{timeframe}'. Skipping.")
        df['signal'] = 'Empty'
        return df

    # --- 2. Initialize Signal Column and Base Data ---
    df['signal'] = 'Empty'
    
    # --- 3. Market Regime Filter (Simplified for screener) ---
    trade_allowed_by_regime = pd.Series(True, index=df.index)

    # --- 4. Higher Timeframe Trend Confirmation (Simplified for screener) ---
    htf_trend_ok = pd.Series(True, index=df.index)

    # --- 5. Volume Confirmation (Simplified for screener) ---
    volume_ok = pd.Series(True, index=df.index)

    # --- 6. Core Strategy Logic ---
    conditions = []
    
    if strategy_cfg.get('is_uptrend', False):
        conditions.append(df['close'] > df['vwma_slow'])

    if strategy_cfg.get('fast_vwma_above_slow', False):
        conditions.append(df['vwma_fast'] > df['vwma_slow'])

    prox_cfg = strategy_cfg.get('proximity_check', {})
    if prox_cfg.get('enabled', False):
        ma_column = prox_cfg.get('ma_column', 'vwma_slow')
        proximity_pct = prox_cfg.get('proximity_pct', 1.0)
        is_near_ma = (abs(df['close'] - df[ma_column]) / df[ma_column] * 100) <= proximity_pct
        conditions.append(is_near_ma)

    stoch_cfg = strategy_cfg.get('stoch_check', {})
    if stoch_cfg.get('enabled', False):
        k_min = stoch_cfg.get('k_min', 0)
        k_max = stoch_cfg.get('k_max', 100)
        stoch_is_in_range = (df['stoch_k'] >= k_min) & (df['stoch_k'] <= k_max)
        conditions.append(stoch_is_in_range)
        
    if conditions:
        final_buy_condition = pd.concat(conditions, axis=1).all(axis=1)
        final_buy_condition &= trade_allowed_by_regime
        final_buy_condition &= htf_trend_ok
        final_buy_condition &= volume_ok
        
        signal_name = f"Buy ({strategy_name})"
        df.loc[final_buy_condition, 'signal'] = signal_name

    logging.info(f"Signal generation complete for {profile}/{timeframe}. Found signals: \n{df['signal'].value_counts().to_string()}")
    return df
