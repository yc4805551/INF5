import requests
import json

# 测试 Everything API 返回的字段结构
url = "http://localhost:292/"
params = {
    "search": "吴军",
    "json": "1",
    "count": "2",
    "path": "1",  # 返回完整路径
    "size": "1",  # 返回文件大小
    "dm": "1"     # 返回修改日期
}

try:
    response = requests.get(url, params=params, auth=("yc", "abcd1234"), timeout=5)
    response.raise_for_status()
    data = response.json()
    
    print("=" * 50)
    print("Everything API Response Structure:")
    print("=" * 50)
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    if 'results' in data and len(data['results']) > 0:
        print("\n" + "=" * 50)
        print("First Result Fields:")
        print("=" * 50)
        first_result = data['results'][0]
        for key, value in first_result.items():
            print(f"{key}: {type(value).__name__} = {value}")
    
except Exception as e:
    print(f"Error: {e}")
