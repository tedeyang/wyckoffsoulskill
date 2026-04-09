# -*- coding: utf-8 -*-
"""
Generate stock_constants.py with full A-share stock list
Uses retry mechanism to handle network issues
"""

import time
import json


def fetch_stock_list_with_retry(max_retries=5, delay=2):
    """Fetch full A-share stock list with retry mechanism"""
    import akshare as ak
    
    for attempt in range(max_retries):
        try:
            print(f"尝试 {attempt + 1}/{max_retries}: 获取全A股列表...")
            
            # Method 1: stock_info_a_code_name (新浪)
            df = ak.stock_info_a_code_name()
            
            if len(df) > 5000:  # Verify we got reasonable amount of data
                print(f"✅ 成功获取 {len(df)} 只股票")
                return df
            else:
                print(f"⚠️ 数据量不足: {len(df)} 只，重试...")
                
        except Exception as e:
            print(f"❌ 失败: {e}")
            if attempt < max_retries - 1:
                print(f"等待 {delay} 秒后重试...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
    
    raise Exception(f"Failed to fetch stock list after {max_retries} attempts")


def generate_constants_file(output_file='stock_constants.py'):
    """Generate the stock_constants.py file"""
    
    # Fetch stock list
    df = fetch_stock_list_with_retry()
    
    # Clean data
    df['code'] = df['code'].astype(str).str.strip()
    df['name'] = df['name'].astype(str).str.strip()
    
    # Build mappings
    stock_map = {}  # code -> name
    name_to_code = {}  # name -> code
    
    for _, row in df.iterrows():
        code = row['code']
        name = row['name']
        
        if len(code) == 6 and code.isdigit():
            stock_map[code] = name
            # Only map clean names (no special chars)
            if name and not name.startswith('*') and 'ST' not in name:
                name_to_code[name] = code
    
    print(f"\n整理数据:")
    print(f"  代码->名称: {len(stock_map)} 条")
    print(f"  名称->代码: {len(name_to_code)} 条")
    
    # Generate common aliases
    aliases = generate_aliases(name_to_code)
    
    # Write to file
    print(f"\n写入文件: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('# -*- coding: utf-8 -*-\n')
        f.write('# Auto-generated stock name -> code mapping\n')
        f.write(f'# Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'# Total stocks: {len(stock_map)}\n\n')
        
        # Write name to code mapping
        f.write('STOCK_NAME_TO_CODE = {\n')
        for name in sorted(name_to_code.keys()):
            code = name_to_code[name]
            # Escape quotes in name
            safe_name = name.replace("'", "\\'")
            f.write(f"    '{safe_name}': '{code}',\n")
        f.write('}\n\n')
        
        # Write code to name mapping
        f.write('STOCK_CODE_TO_NAME = {\n')
        for code in sorted(stock_map.keys()):
            name = stock_map[code]
            safe_name = name.replace("'", "\\'")
            f.write(f"    '{code}': '{safe_name}',\n")
        f.write('}\n\n')
        
        # Write aliases
        f.write('STOCK_ALIASES = {\n')
        f.write('    # Common aliases and abbreviations\n')
        for alias, full_name in sorted(aliases.items()):
            safe_alias = alias.replace("'", "\\'")
            safe_full = full_name.replace("'", "\\'")
            f.write(f"    '{safe_alias}': '{safe_full}',\n")
        f.write('}\n\n')
        
        # Write helper functions
        f.write('def get_all_stock_names():\n')
        f.write('    """Return all available stock names"""\n')
        f.write('    return list(STOCK_NAME_TO_CODE.keys())\n\n')
        
        f.write('def get_all_stock_codes():\n')
        f.write('    """Return all available stock codes"""\n')
        f.write('    return list(STOCK_CODE_TO_NAME.keys())\n\n')
        
        f.write('def get_stock_count():\n')
        f.write('    """Return total number of stocks"""\n')
        f.write(f'    return {len(stock_map)}\n')
    
    print(f"✅ 完成! 共写入 {len(stock_map)} 只股票")
    return len(stock_map)


def generate_aliases(name_to_code):
    """Generate common aliases for stock names"""
    aliases = {}
    
    # Common company abbreviations
    common_patterns = {
        '贵州茅台': ['茅台'],
        '五粮液': ['五粮液'],
        '宁德时代': ['宁德', 'CATL'],
        '比亚迪': ['BYD', '比亚'],
        '招商银行': ['招行'],
        '平安银行': ['平安银'],
        '中国平安': ['平安'],
        '美的集团': ['美的'],
        '格力电器': ['格力'],
        '海尔智家': ['海尔'],
        '迈瑞医疗': ['迈瑞'],
        '药明康德': ['药明'],
        '恒瑞医药': ['恒瑞'],
        '爱尔眼科': ['爱尔'],
        '片仔癀': ['片仔癀'],
        '隆基绿能': ['隆基'],
        '通威股份': ['通威'],
        '阳光电源': ['阳光电源'],
        '科大讯飞': ['讯飞', '科大讯飞'],
        '京东方A': ['京东方'],
        '中兴通讯': ['中兴'],
        '三六零': ['360'],
        '中国联通': ['联通'],
        '中国移动': ['移动'],
        '中国电信': ['电信'],
        '中国中免': ['中免'],
        '牧原股份': ['牧原'],
        '温氏股份': ['温氏'],
        '正邦科技': ['正邦'],
        '天邦食品': ['天邦'],
        '华统股份': ['华统'],
        '通富微电': ['通富', '通富微电'],
        '北方华创': ['北方华创'],
        '韦尔股份': ['韦尔'],
        '兆易创新': ['兆易'],
        '中芯国际': ['中芯'],
        '长电科技': ['长电'],
        '澜起科技': ['澜起'],
        '中微公司': ['中微'],
        '寒武纪': ['寒武纪'],
        '海光信息': ['海光'],
        '华天科技': ['华天'],
        '晶方科技': ['晶方'],
        '士兰微': ['士兰微'],
        '紫光国微': ['紫光国微'],
        '北京君正': ['君正'],
        '圣邦股份': ['圣邦'],
        '卓胜微': ['卓胜微'],
        '景嘉微': ['景嘉微'],
        '斯达半导': ['斯达'],
        '汇川技术': ['汇川'],
        '三一重工': ['三一'],
        '恒立液压': ['恒立'],
        '伊利股份': ['伊利'],
        '海天味业': ['海天'],
        '山西汾酒': ['汾酒'],
        '泸州老窖': ['老窖', '泸洲老窖'],
        '洋河股份': ['洋河'],
        '古井贡酒': ['古井'],
        '中国神华': ['神华'],
        '长江电力': ['长电'],
        '中信证券': ['中信证'],
        '东方财富': ['东财'],
        '华泰证券': ['华泰'],
        '国泰君安': ['国君'],
        '海通证券': ['海通'],
        '广发证券': ['广发'],
        '申万宏源': ['申万'],
        '中金公司': ['中金'],
        '兴业证券': ['兴业证'],
    }
    
    for full_name, alias_list in common_patterns.items():
        if full_name in name_to_code:
            for alias in alias_list:
                aliases[alias] = full_name
    
    return aliases


if __name__ == '__main__':
    try:
        count = generate_constants_file()
        print(f"\n🎉 成功生成包含 {count} 只股票的常量表")
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()
