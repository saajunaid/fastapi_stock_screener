# your_logic/divergence_calculator.py
import pandas as pd
import numpy as np
from scipy.signal import find_peaks
import logging

def find_divergence(df, div_cfg):
    """
    Finds bullish and bearish divergences between price and an oscillator.
    """
    if not div_cfg or not div_cfg.get('enabled', False):
        df['bullish_divergence'] = False
        df['bearish_divergence'] = False
        return df

    oscillator = div_cfg.get('oscillator', 'stoch_k')
    pivots_cfg = div_cfg.get('pivots', {'left': 3, 'right': 3})
    prominence = div_cfg.get('prominence', 0.1)

    if oscillator not in df.columns or not pd.api.types.is_numeric_dtype(df[oscillator]):
        logging.warning(f"Oscillator '{oscillator}' not found or not numeric. Skipping divergence calculation.")
        df['bullish_divergence'] = False
        df['bearish_divergence'] = False
        return df

    osc_data = df[oscillator].dropna()
    if osc_data.empty:
        df['bullish_divergence'] = False
        df['bearish_divergence'] = False
        return df

    # Using distance for separation between peaks
    peak_distance = pivots_cfg.get('left', 5) + pivots_cfg.get('right', 5)

    low_peaks, _ = find_peaks(-df['low'], prominence=prominence, distance=peak_distance)
    osc_low_peaks, _ = find_peaks(-osc_data, prominence=prominence, distance=peak_distance)
    
    df['bullish_divergence'] = False
    df['bearish_divergence'] = False # Placeholder for future use

    # Create a series for easier mapping
    price_lows = pd.Series(df['low'].iloc[low_peaks].values, index=df.index[low_peaks])
    osc_lows = pd.Series(osc_data.iloc[osc_low_peaks].values, index=osc_data.index[osc_low_peaks])

    if 'regular_bullish' in div_cfg.get('types', {}).get('buy', []):
        for i in range(1, len(price_lows)):
            current_price_low_val = price_lows.iloc[i]
            prev_price_low_val = price_lows.iloc[i-1]
            current_price_low_idx = price_lows.index[i]
            prev_price_low_idx = price_lows.index[i-1]

            # Condition: Lower low in price
            if current_price_low_val < prev_price_low_val:
                # Find corresponding oscillator lows in the same time window
                osc_window = osc_lows[(osc_lows.index >= prev_price_low_idx) & (osc_lows.index <= current_price_low_idx)]
                
                if len(osc_window) >= 2:
                    # Condition: Higher low in oscillator
                    if osc_window.iloc[-1] > osc_window.iloc[0]:
                        df.loc[current_price_low_idx, 'bullish_divergence'] = True
    
    return df
