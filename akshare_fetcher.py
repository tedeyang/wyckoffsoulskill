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
    # Use normalized names for matching
    query_normalized = normalize_name(query)
    for name, code in STOCK_NAME_TO_CODE.items():
        name_normalized = normalize_name(name)
        if query_normalized in name_normalized:
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
    """Calculate volume profile"""
    if pd is None:
        pd = _import_pandas()
    if len(df) < 10 or 'volume' not in df.columns:
        return {}
    
    price_range = df['high'].max() - df['low'].min()
    if price_range == 0:
        return {}
    
    df = df.copy()
    df['typical'] = (df['high'] + df['low'] + df['close']) / 3
    df['typical'] = pd.to_numeric(df['typical'], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
    
    price_volume = df.groupby(pd.cut(df['typical'], bins=10))['volume'].sum()
    price_volume = price_volume.dropna()
    
    if len(price_volume) == 0:
        return {}
    
    poc_bin = price_volume.idxmax()
    poc_price = (poc_bin.left + poc_bin.right) / 2
    
    total_vol = price_volume.sum()
    cumsum = price_volume.sort_values(ascending=False).cumsum()
    value_area_bins = cumsum[cumsum <= total_vol * 0.7].index
    
    if len(value_area_bins) > 0:
        va_low = min([b.left for b in value_area_bins])
        va_high = max([b.right for b in value_area_bins])
    else:
        va_low = va_high = poc_price
    
    return {'poc': round(poc_price, 2), 'value_area_low': round(va_low, 2), 'value_area_high': round(va_high, 2)}


def analyze_last_day_minute(minute5_df, daily_df, pd=None):
    """Detailed analysis of last trading day's minute data"""
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
    
    supply_bars = demand_bars = 0
    vol_median = today_df['volume'].median()
    for _, bar in today_df.iterrows():
        spread = bar['high'] - bar['low']
        if spread > 0:
            close_pos = (bar['close'] - bar['low']) / spread
            if close_pos > 0.7 and bar['volume'] > vol_median:
                demand_bars += 1
            elif close_pos < 0.3 and bar['volume'] > vol_median:
                supply_bars += 1
    
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
    Calculate Wyckoff Point & Figure chart
    Box size = LTP * box_pct (default 1%)
    Reversal = reversal_boxes boxes (default 3)
    Returns P&F columns and price targets based on horizontal count
    """
    if len(daily_df) < 50:
        return {'error': 'Insufficient data'}
    
    pd = _import_pandas()
    np = _import_numpy()
    
    # Use last 200 days
    df = daily_df.tail(200).copy()
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df['low'] = pd.to_numeric(df['low'], errors='coerce')
    
    ltp = float(df['close'].iloc[-1])
    box_size = ltp * box_pct
    
    # Round box size to reasonable precision
    if box_size >= 1:
        box_size = round(box_size, 2)
    elif box_size >= 0.1:
        box_size = round(box_size, 2)
    else:
        box_size = round(box_size, 3)
    
    reversal_amount = box_size * reversal_boxes
    
    # Build P&F columns
    columns = []  # Each column: {'type': 'X'/'O', 'boxes': count, 'price_levels': [(low, high)]}
    current_col = None
    
    for idx, row in df.iterrows():
        high = float(row['high'])
        low = float(row['low'])
        
        if current_col is None:
            # Initialize first column based on first day direction
            if high >= low + box_size:
                boxes = int((high - low) / box_size) + 1
                current_col = {
                    'type': 'X',
                    'start_price': low,
                    'end_price': low + boxes * box_size,
                    'boxes': boxes,
                    'high': high,
                    'low': low
                }
            else:
                current_col = {
                    'type': 'O',
                    'start_price': high,
                    'end_price': high - box_size,
                    'boxes': 1,
                    'high': high,
                    'low': low
                }
        elif current_col['type'] == 'X':
            # Check for continuation
            potential_boxes = int((high - current_col['end_price']) / box_size)
            if potential_boxes > 0:
                current_col['boxes'] += potential_boxes
                current_col['end_price'] += potential_boxes * box_size
                current_col['high'] = max(current_col['high'], high)
            # Check for reversal
            elif current_col['end_price'] - low >= reversal_amount:
                columns.append(current_col)
                boxes = int((current_col['end_price'] - low) / box_size)
                current_col = {
                    'type': 'O',
                    'start_price': current_col['end_price'],
                    'end_price': current_col['end_price'] - boxes * box_size,
                    'boxes': boxes,
                    'high': high,
                    'low': low
                }
        else:  # current_col['type'] == 'O'
            # Check for continuation
            potential_boxes = int((current_col['end_price'] - low) / box_size)
            if potential_boxes > 0:
                current_col['boxes'] += potential_boxes
                current_col['end_price'] -= potential_boxes * box_size
                current_col['low'] = min(current_col['low'], low)
            # Check for reversal
            elif high - current_col['end_price'] >= reversal_amount:
                columns.append(current_col)
                boxes = int((high - current_col['end_price']) / box_size)
                current_col = {
                    'type': 'X',
                    'start_price': current_col['end_price'],
                    'end_price': current_col['end_price'] + boxes * box_size,
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
        """Find a congestion area starting from given index"""
        if start_idx >= len(columns):
            return None
        
        # Get price range for columns
        prices = []
        for col in columns[start_idx:min(start_idx + max_cols, len(columns))]:
            col_low = min(col['start_price'], col.get('end_price', col['start_price']))
            col_high = max(col['start_price'], col.get('end_price', col['start_price']))
            prices.append((col_low, col_high))
        
        if len(prices) < min_cols:
            return None
        
        # Find overlapping range (congestion)
        for width in range(min_cols, min(len(prices) + 1, max_cols + 1)):
            for start in range(len(prices) - width + 1):
                # Check if these columns form a congestion
                overlap_low = max([p[0] for p in prices[start:start+width]])
                overlap_high = min([p[1] for p in prices[start:start+width]])
                
                if overlap_high > overlap_low:  # There's overlap
                    return {
                        'start_col': start_idx + start,
                        'width': width,
                        'bottom': overlap_low,
                        'top': overlap_high,
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


def fetch_data_parallel(symbol: str, daily_days: int = 120) -> Dict:
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
    
    with ThreadPoolExecutor(max_workers=2) as executor:
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
    
    if 'daily_full' in results:
        try:
            weekly = resample_weekly_fast(results['daily_full'], pd).tail(60).reset_index(drop=True)
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
    data = fetch_data_parallel(symbol, daily_days=120)
    
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
    import time
    
    test_symbols = ["601869"]
    
    for symbol in test_symbols:
        print(f"\n{'='*60}")
        print(f"Testing {symbol}...")
        print('='*60)
        
        start = time.time()
        try:
            result = quick_analysis_v2(symbol)
            elapsed = time.time() - start
            
            print(f"✅ Success in {elapsed:.3f}s ({result['execution_time_ms']:.0f}ms)")
            
            print(f"\nData Quality:")
            dq = result['data_quality']
            print(f"  日线: {dq['daily_bars']} 根 ({dq['daily_range']})")
            print(f"  周线: {dq['weekly_bars']} 根 ({dq['weekly_range']})")
            print(f"  5分钟: {dq['minute5_bars']} 根 ({dq['minute5_range']})")
            
            print(f"\nKey Levels:")
            for k, v in result['key_levels'].items():
                print(f"  {k}: {v}")
            
            print(f"\nTrend: {result['trend']}")
            print(f"Phase: {result['phase']}")
                
        except Exception as e:
            import traceback
            print(f"❌ Error: {e}")
            traceback.print_exc()
