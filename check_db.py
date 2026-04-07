import sqlite3
conn = sqlite3.connect('filter_engine/data/rules.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM rules')
total = cur.fetchone()[0]
print('Total rules:', total)
cur.execute('SELECT DISTINCT category FROM rules ORDER BY category')
cats = [r[0] for r in cur.fetchall()]
print('Categories:', cats)
cur.execute("SELECT name, category, scene FROM rules WHERE category NOT LIKE '通用-%' LIMIT 30")
rows = cur.fetchall()
print('Non-general rules:')
for r in rows:
    print(' ', r)
conn.close()
