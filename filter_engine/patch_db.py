"""
直接修改数据库中的无效正则规则，在api.py导入时自动执行
"""
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'rules.db')

def patch_invalid_regex():
    """修复数据库中的无效正则表达式"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    fixed_content = json.dumps([
        r"(.)\1{5,}",        # 同一字符重复6次以上（支持中英文及符号）
        r"[a-zA-Z0-9]{20,}", # 长串无意义字母数字
    ], ensure_ascii=False)
    
    cur.execute(
        "UPDATE rules SET content=? WHERE name=?",
        (fixed_content, '通用-垃圾-乱码重复字符')
    )
    rows = cur.rowcount
    conn.commit()
    conn.close()
    return rows

if __name__ == '__main__':
    n = patch_invalid_regex()
    print(f"Patched {n} rule(s).")
