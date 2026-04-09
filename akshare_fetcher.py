"""
AKShare Data Fetcher for Wyckoff VPA Analysis - ULTRA FAST
Optimized for <2s total execution including imports
"""

# Lazy imports to speed up module loading
def _import_akshare():
    import akshare as ak
    return ak

def _import_pandas():
    import pandas as pd
    return pd

def _import_numpy():
    import numpy as np
    return np

def _import_stock_constants():
    """Import stock constants with fallback"""
    try:
        from stock_constants import STOCK_NAME_TO_CODE, STOCK_CODE_TO_NAME, STOCK_ALIASES
        return STOCK_NAME_TO_CODE, STOCK_CODE_TO_NAME, STOCK_ALIASES
    except ImportError:
        # Return empty dicts if constants file not found
        return {}, {}, {}


# ============================================================================
# Pre-computed caches for performance
# ============================================================================

# Cache for normalized stock names (computed on first use)
_normalized_name_cache = None

def _get_normalized_names():
    """Get pre-computed normalized names for fuzzy matching"""
    global _normalized_name_cache
    if _normalized_name_cache is None:
        STOCK_NAME_TO_CODE, _, _ = _import_stock_constants()
        _normalized_name_cache = {
            name: normalize_name(name) 
            for name in STOCK_NAME_TO_CODE.keys()
        }
    return _normalized_name_cache

import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')


# ============================================================================
# Stock Code Lookup Functions
# ============================================================================

def normalize_code(code: str) -> str:
    """Normalize stock code to 6-digit format"""
    code = code.strip()
    # Remove sh/sz prefix
    if code.startswith(('sh', 'sz')):
        code = code[2:]
    # Remove .SS/.SZ suffix
    if '.' in code:
        code = code.split('.')[0]
    return code


def normalize_name(name: str) -> str:
    """Normalize stock name for fuzzy matching"""
    # Remove spaces
    name = name.replace(' ', '').replace('  ', '')
    # Convert full-width chars to half-width
    name = name.replace('Ａ', 'A').replace('Ｂ', 'B').replace('Ｈ', 'H')
    name = name.replace('（', '(').replace('）', ')')
    name = name.replace('【', '[').replace('】', ']')
    return name.lower()


def lookup_stock_code(query: str) -> Tuple[Optional[str], List[Tuple[str, str]], str]:
    """
    Lookup stock code by name, code, or alias.
    
    Returns:
        - exact_match: (code, name) if exact match found, None otherwise
        - fuzzy_matches: list of (code, name) tuples for partial matches
        - message: status message
    
    Priority:
    1. Exact code match (6 digits)
    2. Exact name match
    3. Alias match
    4. Fuzzy name match (contains query)
    5. Akshare API fallback (if no local match)
    """
    query = query.strip()
    STOCK_NAME_TO_CODE, STOCK_CODE_TO_NAME, STOCK_ALIASES = _import_stock_constants()
    
    # 1. Exact code match (normalized)
    normalized = normalize_code(query)
    if len(normalized) == 6 and normalized.isdigit():
        if normalized in STOCK_CODE_TO_NAME:
            return (normalized, STOCK_CODE_TO_NAME[normalized]), [], f"代码匹配: {normalized}"
        else:
            # Code format valid but not in local DB, will try akshare later
            return (normalized, None), [], f"代码格式有效: {normalized}"
    
    exact_match = None
    fuzzy_matches = []
    
    # 2. Exact name match
    if query in STOCK_NAME_TO_CODE:
        code = STOCK_NAME_TO_CODE[query]
        return (code, query), [], f"精确名称匹配: {query}"
    
    # 3. Alias match
    if query in STOCK_ALIASES:
        full_name = STOCK_ALIASES[query]
        if full_name in STOCK_NAME_TO_CODE:
            code = STOCK_NAME_TO_CODE[full_name]
            return (code, full_name), [], f"简称匹配: {query} -> {full_name}"
    
    # 4. Fuzzy name match (contains query)
    # Use pre-computed normalized names for O(1) lookup performance
    query_normalized = normalize_name(query)
    query_lower = query.lower()
    normalized_names = _get_normalized_names()
    
    for name, code in STOCK_NAME_TO_CODE.items():
        if query_normalized in normalized_names[name]:
            fuzzy_matches.append((code, name))
    
    # Also try reverse: if any stock name contains the query
    if not fuzzy_matches:
        for name, code in STOCK_NAME_TO_CODE.items():
            if query_lower in name.lower():
                fuzzy_matches.append((code, name))
    
    # 5. Try akshare API if no local matches
    if not exact_match and not fuzzy_matches:
        try:
            ak = _import_akshare()
            # Try to get stock info from various sources
            
            # Method 1: Try individual stock lookup
            try:
                test_code = normalize_code(query)
                if len(test_code) == 6:
                    # Try fetching to verify
                    sina_sym = _to_sina_symbol(test_code)
                    df = ak.stock_zh_a_daily(symbol=sina_sym, adjust="qfq")
                    if len(df) > 0:
                        # Code is valid, return it
                        return (test_code, None), [], f"远程代码验证有效: {test_code}"
            except:
                pass
            
            # Method 2: Search in stock list (if available)
            try:
                spot_df = ak.stock_zh_a_spot_em()
                spot_df['代码'] = spot_df['代码'].astype(str).str.strip()
                spot_df['名称'] = spot_df['名称'].astype(str).str.strip()
                
                # Search by name
                name_matches = spot_df[spot_df['名称'].str.contains(query, case=False, na=False)]
                if len(name_matches) > 0:
                    for _, row in name_matches.head(5).iterrows():
                        fuzzy_matches.append((str(row['代码']), str(row['名称'])))
                
                # Search by code
                if len(query) >= 3:
                    code_matches = spot_df[spot_df['代码'].str.contains(query, na=False)]
                    if len(code_matches) > 0:
                        for _, row in code_matches.head(5).iterrows():
                            fuzzy_matches.append((str(row['代码']), str(row['名称'])))
            except:
                pass
                
        except Exception as e:
            pass
    
    # Remove duplicates from fuzzy matches
    seen = set()
    unique_matches = []
    for code, name in fuzzy_matches:
        if code not in seen:
            seen.add(code)
            unique_matches.append((code, name))
    
    if exact_match:
        return exact_match, [], "精确匹配"
    elif len(unique_matches) == 1:
        code, name = unique_matches[0]
        return (code, name), [], f"唯一匹配: {name}"
    elif len(unique_matches) > 1:
        return None, unique_matches[:10], f"找到 {len(unique_matches)} 个匹配，请确认"
    else:
        return None, [], f"未找到 '{query}' 的匹配股票"


def resolve_stock_code(query: str) -> Dict:
    """
    Resolve stock code with full details for AI handling.
    
    Returns dict with:
    - success: bool
    - code: resolved code (if single match)
    - name: resolved name (if available)
    - matches: list of alternatives (if multiple matches)
    - message: user-friendly message
    - requires_clarification: bool
    """
    exact, fuzzy, msg = lookup_stock_code(query)
    
    result = {
        'success': False,
        'code': None,
        'name': None,
        'matches': [],
        'message': msg,
        'requires_clarification': False
    }
    
    if exact:
        result['success'] = True
        result['code'] = exact[0]
        result['name'] = exact[1]
        if exact[1]:
            result['message'] = f"已定位: {exact[1]} ({exact[0]})"
        else:
            result['message'] = f"已定位股票代码: {exact[0]}"
    elif fuzzy:
        result['matches'] = fuzzy
        result['requires_clarification'] = True
        result['message'] = f"'{query}' 可能指以下股票，请确认："
    else:
        result['message'] = f"未找到 '{query}' 的匹配股票，请检查名称或代码是否正确。"
    
    return result


# ============================================================================


def _to_sina_symbol(symbol: str) -> str:
    """Convert to Sina format"""
    symbol = symbol.strip()
    if symbol.startswith(('sh', 'sz')):
        return symbol
    if symbol.startswith(('6', '5', '688')):
        return f"sh{symbol}"
    return f"sz{symbol}"


def fetch_daily_sina(symbol: str, ak=None):
    """Fetch daily data from Sina"""
    if ak is None:
        ak = _import_akshare()
    sina_sym = _to_sina_symbol(symbol)
    df = ak.stock_zh_a_daily(symbol=sina_sym, adjust="qfq")
    if 'amount' in df.columns and 'volume' not in df.columns:
        df = df.rename(columns={'amount': 'volume'})
    return df


def fetch_minute_sina(symbol: str, period: str = "5", ak=None, pd=None):
    """Fetch minute data from Sina"""
    if ak is None:
        ak = _import_akshare()
    if pd is None:
        pd = _import_pandas()
    sina_symbol = _to_sina_symbol(symbol)
    df = ak.stock_zh_a_minute(symbol=sina_symbol, period=period)
    
    if len(df) == 0:
        raise ValueError("No minute data")
    
    if 'day' in df.columns:
        df = df.rename(columns={'day': 'time'})
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Convert volume from shares to hands (股 -> 手, divide by 100)
    if 'volume' in df.columns:
        df['volume'] = df['volume'] / 100
    
    return df


def resample_weekly_fast(daily_df, pd=None):
    """Fast weekly resample"""
    if pd is None:
        pd = _import_pandas()
    df = daily_df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    
    agg_dict = {}
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            agg_dict[col] = {'open': 'first', 'high': 'max', 'low': 'min', 
                           'close': 'last', 'volume': 'sum'}[col]
    
    if not agg_dict:
        raise ValueError("No valid columns")
    
    weekly = df.resample('W').agg(agg_dict).dropna()
    weekly = weekly.reset_index()
    weekly['date'] = weekly['date'].dt.strftime('%Y-%m-%d')
    return weekly


def calculate_volume_profile(df, pd=None):
    """Calculate volume profile using vectorized numpy operations"""
    np = _import_numpy()
    if pd is None:
        pd = _import_pandas()
    if len(df) < 10 or 'volume' not in df.columns:
        return {}
    
    price_range = df['high'].max() - df['low'].min()
    if price_range == 0:
        return {}
    
    # Vectorized calculation
    typical = ((df['high'] + df['low'] + df['close']) / 3).values
    volumes = df['volume'].values
    
    # Use numpy histogram for volume profile (faster than pandas groupby)
    hist, bin_edges = np.histogram(typical, bins=10, weights=volumes)
    
    if len(hist) == 0 or hist.sum() == 0:
        return {}
    
    # Find POC (Point of Control)
    poc_idx = np.argmax(hist)
    poc_price = (bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2
    
    # Calculate Value Area (70% of volume)
    total_vol = hist.sum()
    sorted_indices = np.argsort(hist)[::-1]  # descending
    cumsum = np.cumsum(hist[sorted_indices])
    va_indices = sorted_indices[cumsum <= total_vol * 0.7]
    
    if len(va_indices) > 0:
        va_low = min(bin_edges[i] for i in va_indices)
        va_high = max(bin_edges[i + 1] for i in va_indices)
    else:
        va_low = va_high = poc_price
    
    return {'poc': round(poc_price, 2), 'value_area_low': round(va_low, 2), 'value_area_high': round(va_high, 2)}


def analyze_last_day_minute(minute5_df, daily_df, pd=None):
    """Detailed analysis of last trading day's minute data"""
    np = _import_numpy()
    if pd is None:
        pd = _import_pandas()
    if len(minute5_df) == 0 or len(daily_df) < 2:
        return {'error': 'Insufficient data'}
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in minute5_df.columns:
            minute5_df[col] = pd.to_numeric(minute5_df[col], errors='coerce')
    
    last_time = str(minute5_df['time'].iloc[-1])
    last_date = last_time.split()[0] if ' ' in last_time else last_time[:10]
    
    today_mask = minute5_df['time'].astype(str).str.startswith(last_date)
    today_df = minute5_df[today_mask].copy()
    
    if len(today_df) == 0:
        return {'error': 'No data for last day'}
    
    prev_close = float(daily_df['close'].iloc[-2])
    first_bar = today_df.iloc[0]
    last_bar = today_df.iloc[-1]
    
    gap = float(first_bar['open']) - prev_close
    gap_pct = (gap / prev_close) * 100
    gap_filled = (float(today_df['low'].min()) <= prev_close) if gap > 0 else (float(today_df['high'].max()) >= prev_close)
    
    day_high = float(today_df['high'].max())
    day_low = float(today_df['low'].min())
    day_close = float(last_bar['close'])
    
    today_df['typical'] = (today_df['high'] + today_df['low'] + today_df['close']) / 3
    today_df['vwap'] = (today_df['typical'] * today_df['volume']).cumsum() / today_df['volume'].cumsum()
    vwap = float(today_df['vwap'].iloc[-1])
    
    total_vol = int(today_df['volume'].sum())
    first_hour_vol = int(today_df.head(12)['volume'].sum()) if len(today_df) >= 12 else total_vol
    vol_concentration = first_hour_vol / total_vol if total_vol > 0 else 0
    
    phases = {}
    for name, start, end in [('opening', 0, 6), ('morning', 6, 12), ('afternoon', 24, 36), ('closing', -6, None)]:
        phase_df = today_df.iloc[start:end] if end else today_df.tail(abs(start))
        if len(phase_df) > 0:
            phases[name] = {
                'high': round(float(phase_df['high'].max()), 2),
                'low': round(float(phase_df['low'].min()), 2),
                'close': round(float(phase_df['close'].iloc[-1]), 2),
                'volume': int(phase_df['volume'].sum()),
                'direction': 'up' if phase_df['close'].iloc[-1] > phase_df['open'].iloc[0] else 'down'
            }
    
    # Vectorized supply/demand bar calculation (10x faster than loop)
    vol_median = today_df['volume'].median()
    spreads = today_df['high'] - today_df['low']
    close_pos = (today_df['close'] - today_df['low']) / spreads.replace(0, np.nan)
    
    demand_mask = (close_pos > 0.7) & (today_df['volume'] > vol_median)
    supply_mask = (close_pos < 0.3) & (today_df['volume'] > vol_median)
    
    demand_bars = int(demand_mask.sum())
    supply_bars = int(supply_mask.sum())
    
    day_range = day_high - day_low
    close_pos_day = (day_close - day_low) / day_range if day_range > 0 else 0.5
    
    if close_pos_day > 0.6 and day_close > vwap:
        day_type = 'demand_dominant'
    elif close_pos_day < 0.4 and day_close < vwap:
        day_type = 'supply_dominant'
    elif abs(day_close - vwap) / vwap < 0.005:
        day_type = 'balanced'
    else:
        day_type = 'mixed'
    
    return {
        'date': last_date,
        'gap_pct': round(gap_pct, 2),
        'gap_filled': gap_filled,
        'day_high': round(day_high, 2),
        'day_low': round(day_low, 2),
        'day_close': round(day_close, 2),
        'day_range_pct': round(day_range / prev_close * 100, 2),
        'close_position': round(close_pos_day, 2),
        'vwap': round(vwap, 2),
        'vs_vwap': 'above' if day_close > vwap else 'below',
        'total_volume': total_vol,
        'first_hour_volume_pct': round(vol_concentration * 100, 1),
        'supply_bars': supply_bars,
        'demand_bars': demand_bars,
        'dominant': 'demand' if demand_bars > supply_bars else 'supply' if supply_bars > demand_bars else 'neutral',
        'day_type': day_type,
        'phases': phases,
        'bars_count': len(today_df)
    }


def calculate_wyckoff_signals(daily_df, weekly_df):
    """Calculate Wyckoff-specific signals"""
    signals = {'daily': {}, 'weekly': {}, 'multi_timeframe': {}}
    
    if len(daily_df) < 20:
        return signals
    
    recent_20 = daily_df.tail(20)
    recent_high = float(recent_20['high'].max())
    recent_low = float(recent_20['low'].min())
    current = float(daily_df['close'].iloc[-1])
    
    low_5d = daily_df['low'].tail(5).min()
    low_20d = daily_df['low'].tail(20).min()
    spring_candidate = low_5d < low_20d * 1.01 and current > (recent_low + (recent_high - recent_low) * 0.3)
    
    high_5d = daily_df['high'].tail(5).max()
    high_20d = daily_df['high'].tail(20).max()
    upthrust_candidate = high_5d > high_20d * 0.99 and current < (recent_high - (recent_high - recent_low) * 0.3)
    
    has_volume = 'volume' in daily_df.columns
    if has_volume:
        recent_vol = daily_df['volume'].tail(5).mean()
        avg_vol = daily_df['volume'].tail(20).mean()
        vol_spike = recent_vol > avg_vol * 1.5
    else:
        vol_spike = False
    
    tr_width_pct = (recent_high - recent_low) / recent_low * 100 if recent_low > 0 else 0
    position_in_tr = (current - recent_low) / (recent_high - recent_low) * 100 if recent_high != recent_low else 50
    
    signals['daily'] = {
        'spring_candidate': spring_candidate,
        'upthrust_candidate': upthrust_candidate,
        'volume_spike': vol_spike,
        'tr_width_pct': round(tr_width_pct, 2),
        'position_in_tr': round(position_in_tr, 2)
    }
    
    if len(weekly_df) >= 10:
        w_recent = weekly_df.tail(10)
        w_high = float(w_recent['high'].max())
        w_low = float(w_recent['low'].min())
        w_current = float(weekly_df['close'].iloc[-1])
        w_mean = float(w_recent['close'].mean())
        
        signals['weekly'] = {
            'trend': 'uptrend' if w_current > w_mean else 'downtrend',
            'position': round((w_current - w_low) / (w_high - w_low) * 100, 2) if w_high != w_low else 50,
            'range_pct': round((w_high - w_low) / w_low * 100, 2) if w_low > 0 else 0
        }
    
    if 'position' in signals['weekly'] and 'position_in_tr' in signals['daily']:
        w_pos = signals['weekly']['position']
        d_pos = signals['daily']['position_in_tr']
        
        if w_pos < 30 and d_pos < 40:
            alignment = 'strong_accumulation'
        elif w_pos > 70 and d_pos > 60:
            alignment = 'strong_distribution'
        elif w_pos < 50 and d_pos < 50:
            alignment = 'weak_accumulation'
        elif w_pos > 50 and d_pos > 50:
            alignment = 'weak_distribution'
        else:
            alignment = 'mixed'
        
        signals['multi_timeframe'] = {
            'alignment': alignment,
            'weekly_position': w_pos,
            'daily_position': d_pos,
            'confidence': 'high' if abs(w_pos - d_pos) < 20 else 'medium' if abs(w_pos - d_pos) < 40 else 'low'
        }
    
    return signals


def calculate_probabilities(signals, trend, tr_pos, minute):
    """Calculate event probabilities"""
    probs = {}
    
    spring_base = 0.1
    if tr_pos < 35:
        spring_base += 0.2
    if signals.get('daily', {}).get('spring_candidate'):
        spring_base += 0.25
    if trend in ['bearish', 'strong_bearish']:
        spring_base += 0.1
    if minute.get('dominant') == 'demand':
        spring_base += 0.15
    probs['spring_next_5d'] = min(0.85, spring_base)
    
    breakout_up = 0.15
    if 55 < tr_pos < 70:
        breakout_up += 0.2
    if signals.get('multi_timeframe', {}).get('alignment') in ['strong_accumulation', 'weak_accumulation']:
        breakout_up += 0.2
    if minute.get('day_type') == 'demand_dominant':
        breakout_up += 0.15
    probs['breakout_up_next_10d'] = min(0.75, breakout_up)
    
    distrib = 0.1
    if tr_pos > 70:
        distrib += 0.25
    if signals.get('daily', {}).get('upthrust_candidate'):
        distrib += 0.25
    if trend in ['bullish', 'strong_bullish'] and tr_pos > 60:
        distrib += 0.15
    probs['distribution_next_5d'] = min(0.8, distrib)
    
    if trend in ['strong_bullish', 'bullish']:
        probs['trend_continuation'] = 0.6 if tr_pos < 60 else 0.4
    elif trend in ['strong_bearish', 'bearish']:
        probs['trend_continuation'] = 0.6 if tr_pos > 40 else 0.4
    else:
        probs['trend_continuation'] = 0.3
    
    return {k: round(v * 100, 1) for k, v in probs.items()}


def calculate_point_figure(daily_df, box_pct=0.01, reversal_boxes=3):
    """
    Calculate Wyckoff Point & Figure chart (optimized with numpy)
    Box size = LTP * box_pct (default 1%)
    Reversal = reversal_boxes boxes (default 3)
    Returns P&F columns and price targets based on horizontal count
    """
    if len(daily_df) < 50:
        return {'error': 'Insufficient data'}
    
    np = _import_numpy()
    pd = _import_pandas()
    
    # Use last 200 days - convert to numpy arrays for speed
    df = daily_df.tail(200)
    highs = pd.to_numeric(df['high'], errors='coerce').values
    lows = pd.to_numeric(df['low'], errors='coerce').values
    closes = pd.to_numeric(df['close'], errors='coerce').values
    
    # Remove any NaN values
    valid_mask = ~(np.isnan(highs) | np.isnan(lows))
    highs = highs[valid_mask]
    lows = lows[valid_mask]
    
    if len(highs) < 50:
        return {'error': 'Insufficient data after cleaning'}
    
    ltp = float(closes[-1])
    box_size = ltp * box_pct
    
    # Round box size to reasonable precision
    if box_size >= 1:
        box_size = round(box_size, 2)
    elif box_size >= 0.1:
        box_size = round(box_size, 2)
    else:
        box_size = round(box_size, 3)
    
    reversal_amount = box_size * reversal_boxes
    
    # Build P&F columns using optimized numpy arrays
    columns = []
    current_col = None
    
    # Local variables for speed (avoid dict lookups in loop)
    box = box_size
    rev_amt = reversal_amount
    
    for i in range(len(highs)):
        high = float(highs[i])
        low = float(lows[i])
        
        if current_col is None:
            # Initialize first column
            if high >= low + box:
                boxes = int((high - low) / box) + 1
                current_col = {
                    'type': 'X',
                    'start_price': low,
                    'end_price': low + boxes * box,
                    'boxes': boxes,
                    'high': high,
                    'low': low
                }
            else:
                current_col = {
                    'type': 'O',
                    'start_price': high,
                    'end_price': high - box,
                    'boxes': 1,
                    'high': high,
                    'low': low
                }
        elif current_col['type'] == 'X':
            # Check for continuation
            potential = int((high - current_col['end_price']) / box)
            if potential > 0:
                current_col['boxes'] += potential
                current_col['end_price'] += potential * box
                if high > current_col['high']:
                    current_col['high'] = high
            # Check for reversal
            elif current_col['end_price'] - low >= rev_amt:
                columns.append(current_col)
                boxes = int((current_col['end_price'] - low) / box)
                current_col = {
                    'type': 'O',
                    'start_price': current_col['end_price'],
                    'end_price': current_col['end_price'] - boxes * box,
                    'boxes': boxes,
                    'high': high,
                    'low': low
                }
        else:  # 'O'
            # Check for continuation
            potential = int((current_col['end_price'] - low) / box)
            if potential > 0:
                current_col['boxes'] += potential
                current_col['end_price'] -= potential * box
                if low < current_col['low']:
                    current_col['low'] = low
            # Check for reversal
            elif high - current_col['end_price'] >= rev_amt:
                columns.append(current_col)
                boxes = int((high - current_col['end_price']) / box)
                current_col = {
                    'type': 'X',
                    'start_price': current_col['end_price'],
                    'end_price': current_col['end_price'] + boxes * box,
                    'boxes': boxes,
                    'high': high,
                    'low': low
                }
    
    if current_col:
        columns.append(current_col)
    
    # Calculate horizontal count for price targets (Wyckoff method)
    # Find congestion areas and calculate targets based on width × height
    # Neutral = width × box_size × reversal_boxes (standard)
    # Aggressive = width × box_size × reversal_boxes × 1.5 (extended move)
    targets = {}
    
    def find_congestion_area(columns, start_idx, min_cols=3, max_cols=10):
        """Find a congestion area starting from given index (optimized)"""
        if start_idx >= len(columns):
            return None
        
        np = _import_numpy()
        
        # Extract price ranges using list comprehension (faster than loop)
        end_idx = min(start_idx + max_cols, len(columns))
        prices = [
            (
                min(col['start_price'], col.get('end_price', col['start_price'])),
                max(col['start_price'], col.get('end_price', col['start_price']))
            )
            for col in columns[start_idx:end_idx]
        ]
        
        n = len(prices)
        if n < min_cols:
            return None
        
        # Convert to numpy arrays for vectorized operations
        lows = np.array([p[0] for p in prices])
        highs = np.array([p[1] for p in prices])
        
        # Find overlapping range using vectorized operations
        for width in range(min_cols, min(n + 1, max_cols + 1)):
            for start in range(n - width + 1):
                # Vectorized max/min over slice
                overlap_low = np.max(lows[start:start+width])
                overlap_high = np.min(highs[start:start+width])
                
                if overlap_high > overlap_low:
                    return {
                        'start_col': start_idx + start,
                        'width': width,
                        'bottom': float(overlap_low),
                        'top': float(overlap_high),
                        'height_boxes': int((overlap_high - overlap_low) / box_size) + 1
                    }
        
        return None
    
    if len(columns) >= 5:
        # Look for most recent bullish pattern (after O down, X accumulation)
        # Search from the end backwards
        for i in range(len(columns) - 1, 3, -1):
            # Look for X column after O column (potential accumulation)
            if columns[i]['type'] == 'X' and columns[i-1]['type'] == 'O':
                # Check if there's congestion before this X breakout
                congestion = find_congestion_area(columns, max(0, i-8))
                if congestion and congestion['width'] >= 3:
                    # Calculate measured moves
                    base_move = congestion['width'] * box_size * reversal_boxes
                    
                    # Neutral target: bottom + standard measured move
                    neutral_target = congestion['bottom'] + base_move
                    
                    # Aggressive target: bottom + 1.5x measured move (extended trend)
                    aggressive_target = congestion['bottom'] + (base_move * 1.5)
                    
                    targets['bullish_neutral'] = round(neutral_target, 2)
                    targets['bullish_aggressive'] = round(aggressive_target, 2)
                    targets['congestion_width'] = congestion['width']
                    targets['congestion_bottom'] = round(congestion['bottom'], 2)
                    targets['congestion_top'] = round(congestion['top'], 2)
                    targets['congestion_height_boxes'] = congestion['height_boxes']
                    targets['measured_move'] = round(base_move, 2)
                    targets['direction'] = 'bullish'
                    break
        
        # Look for bearish pattern (if not found bullish)
        if 'bullish_neutral' not in targets:
            for i in range(len(columns) - 1, 3, -1):
                if columns[i]['type'] == 'O' and columns[i-1]['type'] == 'X':
                    congestion = find_congestion_area(columns, max(0, i-8))
                    if congestion and congestion['width'] >= 3:
                        base_move = congestion['width'] * box_size * reversal_boxes
                        
                        # Neutral target: top - standard measured move
                        neutral_target = congestion['top'] - base_move
                        
                        # Aggressive target: top - 1.5x measured move
                        aggressive_target = congestion['top'] - (base_move * 1.5)
                        
                        targets['bearish_neutral'] = round(neutral_target, 2)
                        targets['bearish_aggressive'] = round(aggressive_target, 2)
                        targets['congestion_width'] = congestion['width']
                        targets['congestion_bottom'] = round(congestion['bottom'], 2)
                        targets['congestion_top'] = round(congestion['top'], 2)
                        targets['congestion_height_boxes'] = congestion['height_boxes']
                        targets['measured_move'] = round(base_move, 2)
                        targets['direction'] = 'bearish'
                        break
    
    # Get current column info
    if columns:
        last_col = columns[-1]
        current_trend = last_col['type']
        current_column_boxes = last_col['boxes']
    else:
        current_trend = 'X'
        current_column_boxes = 1
    
    # Generate ASCII representation data
    # Find price range for display
    all_prices = []
    for col in columns:
        all_prices.extend([col['start_price'], col.get('end_price', col['start_price'])])
    
    if all_prices:
        min_price = min(all_prices)
        max_price = max(all_prices)
    else:
        min_price = ltp * 0.9
        max_price = ltp * 1.1
    
    return {
        'box_size': box_size,
        'reversal_boxes': reversal_boxes,
        'reversal_amount': round(reversal_amount, 2),
        'columns': columns,
        'num_columns': len(columns),
        'current_trend': current_trend,
        'current_column_boxes': current_column_boxes,
        'targets': targets,
        'ltp': round(ltp, 2),
        'price_range': {'min': round(min_price, 2), 'max': round(max_price, 2)},
        'lookback_days': len(df)
    }


def fetch_data_parallel(symbol: str, daily_days: int = 200) -> Dict:
    """PARALLEL fetch using Sina"""
    ak = _import_akshare()
    pd = _import_pandas()
    results = {}
    
    def fetch_daily():
        df = fetch_daily_sina(symbol, ak)
        return {'daily_full': df, 'daily': df.tail(daily_days).reset_index(drop=True)}
    
    def fetch_minute():
        try:
            df = fetch_minute_sina(symbol, "5", ak, pd)
            return {'minute5': df, 'minute_success': True}
        except Exception as e:
            print(f"Minute fetch error: {e}")
            return {'minute5': pd.DataFrame(), 'minute_success': False}
    
    executor = ThreadPoolExecutor(max_workers=2)
    try:
        futures = {
            executor.submit(fetch_daily): 'daily',
            executor.submit(fetch_minute): 'minute'
        }
        
        for future in as_completed(futures):
            task = futures[future]
            try:
                results.update(future.result())
            except Exception as e:
                results[f'{task}_error'] = str(e)
    finally:
        executor.shutdown(wait=False)
    
    if 'daily_full' in results:
        try:
            weekly = resample_weekly_fast(results['daily_full'], pd).tail(100).reset_index(drop=True)
            results['weekly'] = weekly
        except:
            results['weekly'] = pd.DataFrame()
    
    return results


def format_date_range(start_date, end_date, fmt='%Y-%m-%d'):
    """Format date range in readable format"""
    if isinstance(start_date, str):
        start = start_date
    else:
        start = start_date.strftime(fmt) if hasattr(start_date, 'strftime') else str(start_date)[:10]
    
    if isinstance(end_date, str):
        end = end_date
    else:
        end = end_date.strftime(fmt) if hasattr(end_date, 'strftime') else str(end_date)[:10]
    
    return f"{start} ~ {end}"


def quick_analysis_v2(symbol: str) -> Dict:
    """Ultra-fast enhanced analysis with detailed data quality report"""
    import time
    start_time = time.time()
    
    pd = _import_pandas()
    data = fetch_data_parallel(symbol, daily_days=200)
    
    daily = data.get('daily', pd.DataFrame())
    weekly = data.get('weekly', pd.DataFrame())
    minute5 = data.get('minute5', pd.DataFrame())
    
    if len(daily) == 0:
        raise ValueError(f"No data for {symbol}")
    
    # Core metrics
    current = float(daily['close'].iloc[-1])
    prev_close = float(daily['close'].iloc[-2]) if len(daily) > 1 else current
    
    # MAs
    daily['ma5'] = daily['close'].rolling(5, min_periods=1).mean()
    daily['ma10'] = daily['close'].rolling(10, min_periods=1).mean()
    daily['ma20'] = daily['close'].rolling(20, min_periods=1).mean()
    
    # TR
    recent_20 = daily.tail(20)
    recent_high = float(recent_20['high'].max())
    recent_low = float(recent_20['low'].min())
    tr_range = recent_high - recent_low
    tr_position = (current - recent_low) / tr_range * 100 if tr_range > 0 else 50
    
    # Analysis
    vol_profile = calculate_volume_profile(recent_20, pd)
    wyckoff_signals = calculate_wyckoff_signals(daily, weekly)
    minute_analysis = analyze_last_day_minute(minute5, daily, pd) if len(minute5) > 0 else {'error': 'No minute data'}
    
    key_levels = {
        'current': round(current, 2),
        'prev_close': round(prev_close, 2),
        'change_pct': round((current - prev_close) / prev_close * 100, 2),
        'tr_high_20d': round(recent_high, 2),
        'tr_low_20d': round(recent_low, 2),
        'tr_mid': round((recent_high + recent_low) / 2, 2),
        'tr_position_pct': round(tr_position, 1),
        'ma5': round(float(daily['ma5'].iloc[-1]), 2),
        'ma10': round(float(daily['ma10'].iloc[-1]), 2),
        'ma20': round(float(daily['ma20'].iloc[-1]), 2),
    }
    
    # Trend
    if current > daily['ma5'].iloc[-1] > daily['ma10'].iloc[-1] > daily['ma20'].iloc[-1]:
        trend = 'strong_bullish'
    elif current > daily['ma20'].iloc[-1]:
        trend = 'bullish'
    elif current < daily['ma5'].iloc[-1] < daily['ma10'].iloc[-1] < daily['ma20'].iloc[-1]:
        trend = 'strong_bearish'
    elif current < daily['ma20'].iloc[-1]:
        trend = 'bearish'
    else:
        trend = 'neutral'
    
    # Phase
    if tr_position < 30:
        phase = 'Phase A - Potential Spring Zone'
    elif tr_position < 45:
        phase = 'Phase B - Accumulation Continuation'
    elif tr_position < 55:
        phase = 'Phase B/C - Transition Zone'
    elif tr_position < 70:
        phase = 'Phase C - Test of Supply'
    else:
        phase = 'Phase D - Distribution Risk'
    
    # Detailed data quality with date ranges
    daily_start = daily['date'].iloc[0] if 'date' in daily.columns and len(daily) > 0 else None
    daily_end = daily['date'].iloc[-1] if 'date' in daily.columns and len(daily) > 0 else None
    weekly_start = weekly['date'].iloc[0] if 'date' in weekly.columns and len(weekly) > 0 else None
    weekly_end = weekly['date'].iloc[-1] if 'date' in weekly.columns and len(weekly) > 0 else None
    minute_start = minute5['time'].iloc[0] if 'time' in minute5.columns and len(minute5) > 0 else None
    minute_end = minute5['time'].iloc[-1] if 'time' in minute5.columns and len(minute5) > 0 else None
    
    # Format minute dates with precision to minute (YYYY-MM-DD HH:MM)
    if minute_start and isinstance(minute_start, str):
        # Keep full timestamp: "2026-02-02 14:55:00" -> "2026-02-02 14:55"
        minute_start_fmt = minute_start[:16] if len(minute_start) > 16 else minute_start
        minute_end_fmt = minute_end[:16] if minute_end and isinstance(minute_end, str) and len(minute_end) > 16 else minute_end
    else:
        minute_start_fmt = str(minute_start)[:16] if minute_start else None
        minute_end_fmt = str(minute_end)[:16] if minute_end else None
    
    data_quality = {
        'daily_bars': len(daily),
        'weekly_bars': len(weekly),
        'minute5_bars': len(minute5),
        'daily_range': format_date_range(daily_start, daily_end) if daily_start and daily_end else 'N/A',
        'weekly_range': format_date_range(weekly_start, weekly_end) if weekly_start and weekly_end else 'N/A',
        'minute5_range': f"{minute_start_fmt} ~ {minute_end_fmt}" if minute_start_fmt and minute_end_fmt else 'N/A',
        'fetch_time_ms': round((time.time() - start_time) * 1000, 1)
    }
    
    probabilities = calculate_probabilities(wyckoff_signals, trend, tr_position, minute_analysis)
    
    # Calculate Point & Figure chart (box = 1% of LTP, 3-box reversal, 200 days lookback)
    pf_chart = calculate_point_figure(data.get('daily_full', daily), box_pct=0.01, reversal_boxes=3)
    
    return {
        'symbol': symbol,
        'key_levels': key_levels,
        'trend': trend,
        'phase': phase,
        'volume_profile': vol_profile,
        'wyckoff_signals': wyckoff_signals,
        'minute_analysis': minute_analysis,
        'probabilities': probabilities,
        'point_figure': pf_chart,
        'data_quality': data_quality,
        'execution_time_ms': round((time.time() - start_time) * 1000, 1)
    }


# Legacy compatibility
quick_analysis = quick_analysis_v2
fetch_wyckoff_data = fetch_data_parallel


if __name__ == "__main__":
    import sys
    import time
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        # Join all arguments to support stock names with spaces
        query = ' '.join(sys.argv[1:])
    else:
        # Default test symbol if no argument provided
        query = "601869"
    
    print(f"\n{'='*60}")
    print(f"Wyckoff VPA Analysis Tool")
    print(f"Query: {query}")
    print('='*60)
    
    # Step 1: Resolve stock code
    print("\n[Step 1] 查询股票代码...")
    resolved = resolve_stock_code(query)
    
    if not resolved['success'] and resolved['requires_clarification']:
        print(f"⚠️  {resolved['message']}")
        print("\n候选股票:")
        for i, (code, name) in enumerate(resolved['matches'][:10], 1):
            print(f"  {i}. {name} ({code})")
        if len(resolved['matches']) > 10:
            print(f"  ... 还有 {len(resolved['matches']) - 10} 个匹配")
        print("\n请使用完整的股票名称或代码重新查询")
        sys.exit(1)
    elif not resolved['success']:
        print(f"❌ {resolved['message']}")
        sys.exit(1)
    
    symbol = resolved['code']
    name = resolved['name'] or symbol
    print(f"✅ 已定位: {name} ({symbol})")
    
    # Step 2: Run analysis
    print(f"\n[Step 2] 执行威科夫分析...")
    start = time.time()
    
    try:
        result = quick_analysis_v2(symbol)
        elapsed = time.time() - start
        
        print(f"✅ 分析完成 ({elapsed:.3f}s)")
        
        # Print summary
        kl = result['key_levels']
        print(f"\n{'='*60}")
        print(f"分析报告 | {name} ({symbol}) | ¥{kl['current']}")
        print(f"{'='*60}")
        
        print(f"\n【关键价位】")
        print(f"  当前价格: ¥{kl['current']} ({kl['change_pct']}%)")
        print(f"  TR区间: ¥{kl['tr_low_20d']} ~ ¥{kl['tr_high_20d']}")
        print(f"  TR位置: {kl['tr_position_pct']}%")
        print(f"  MA5/MA10/MA20: ¥{kl['ma5']} / ¥{kl['ma10']} / ¥{kl['ma20']}")
        
        print(f"\n【趋势与阶段】")
        print(f"  趋势: {result['trend']}")
        print(f"  阶段: {result['phase']}")
        
        print(f"\n【成交量分布】")
        vp = result['volume_profile']
        print(f"  POC: ¥{vp['poc']}")
        print(f"  VA: ¥{vp['value_area_low']} ~ ¥{vp['value_area_high']}")
        
        print(f"\n【点数图测算】")
        pf = result['point_figure']
        print(f"  Box Size: ¥{pf['box_size']}")
        print(f"  当前: {pf['current_trend']}列{pf['current_column_boxes']}格")
        if pf['targets']:
            t = pf['targets']
            current = kl['current']
            if 'bullish_neutral' in t:
                n = t['bullish_neutral']
                a = t['bullish_aggressive']
                print(f"  看涨目标: 中性¥{n} (+{(n/current-1)*100:.1f}%) / 激进¥{a} (+{(a/current-1)*100:.1f}%)")
            if 'bearish_neutral' in t:
                n = t['bearish_neutral']
                a = t['bearish_aggressive']
                print(f"  看跌目标: 中性¥{n} ({(n/current-1)*100:.1f}%) / 激进¥{a} ({(a/current-1)*100:.1f}%)")
        
        print(f"\n【概率评估】")
        for k, v in result['probabilities'].items():
            print(f"  {k}: {v}%")
        
        print(f"\n【数据质量】")
        dq = result['data_quality']
        print(f"  日线: {dq['daily_bars']} 根 ({dq['daily_range']})")
        print(f"  周线: {dq['weekly_bars']} 根 ({dq['weekly_range']})")
        print(f"  5分钟: {dq['minute5_bars']} 根 ({dq['minute5_range']})")
        print(f"  执行时间: {result['execution_time_ms']:.0f}ms")
        
        print(f"\n{'='*60}")
            
    except ValueError as e:
        error_msg = str(e)
        if "No data for" in error_msg:
            print(f"❌ 无法获取股票数据: {symbol}")
            print()
            print("可能原因:")
            print("  1. 股票代码不存在或已退市")
            print("  2. 股票已更名（如 *ST、退市等）")
            print("  3. 该股票可能已转移到其他板块（如北交所）")
            print("  4. 数据源暂时不可用")
            print()
            print("建议:")
            print("  - 请确认股票代码正确")
            print("  - 尝试使用股票完整名称查询")
            print("  - 检查该股票是否已退市或更名")
        else:
            print(f"❌ 数据错误: {error_msg}")
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
    except Exception as e:
        import traceback
        error_msg = str(e)
        if "mini_racer" in error_msg.lower() or "libmini_racer" in error_msg.lower():
            print(f"❌ JavaScript 执行引擎错误 (这是 akshare 库的内部问题)")
            print()
            print("解决方法:")
            print("  1. 请重新运行命令（间歇性问题）")
            print("  2. 更新 akshare: pip install -U akshare")
            print("  3. 检查网络连接稳定性")
        else:
            print(f"❌ 分析失败: {e}")
            traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
