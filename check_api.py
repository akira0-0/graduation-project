import requests
r = requests.get('http://127.0.0.1:8082/api/rules')
data = r.json()
print('Total:', len(data))
for d in data[:10]:
    print(' ', d['name'], '|', d.get('category',''))
