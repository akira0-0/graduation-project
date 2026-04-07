import sqlite3, json

conn = sqlite3.connect('filter_engine/data/rules.db')
cur = conn.cursor()

# 修复有问题的正则规则，去掉反向引用那条，保留有效的两条
new_content = json.dumps([
    r"(.)\1{5,}",        # 同一字符重复6次以上
    r"[a-zA-Z0-9]{20,}", # 长串无意义字母数字
    r"[\u4e00-\u9fa5]{4,}(?:\1)",  # 替换为简化版重复汉字检测
], ensure_ascii=False)

# 实际上反向引用在json字符串里根本无法工作，直接用更简单的替代方案
fixed_content = json.dumps([
    r"(.)\1{5,}",        # 同一字符重复6次以上（支持中英文）
    r"[a-zA-Z0-9]{20,}", # 长串无意义字母数字
], ensure_ascii=False)

cur.execute("UPDATE rules SET content=? WHERE name=?", (fixed_content, '通用-垃圾-乱码重复字符'))
print('Updated rows:', cur.rowcount)
conn.commit()

# 验证
cur.execute("SELECT content FROM rules WHERE name='通用-垃圾-乱码重复字符'")
row = cur.fetchone()
print('New content:', row[0])
conn.close()
print('Done.')
