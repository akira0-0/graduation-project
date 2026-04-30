import requests
import json
import os

def main():
    api_url = "http://localhost:8123/api/v1/workflows/generate"
    
    # 定义请求数据
    payload = {
        "intent": "创建一个从GitHub获取最新提交并生成周报的工作流",
        "model": "deepseek-chat"
    }
    
    print(f"正在发送请求到 {api_url}...")
    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        if result["status"] == "success":
            print("工作流生成成功！")
            workflow_data = result["workflow"]
            
            # 保存到文件
            output_file = "generated_workflow_api.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(workflow_data, f, indent=2, ensure_ascii=False)
            
            print(f"工作流已保存至: {os.path.abspath(output_file)}")
            
            # 打印部分预览
            print("\n生成的工作流预览:")
            print(json.dumps(workflow_data, indent=2, ensure_ascii=False)[:500] + "...\n")
        else:
            print(f"生成失败: {result}")
            
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到服务器。请确保服务器已启动。")
        print("启动命令: .venv/bin/python workflow_engine/api/server.py")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"错误: 404 Not Found。请检查 API 路径是否正确，或者端口 8000 是否被其他服务占用。")
        else:
            print(f"HTTP 错误: {e}")
            try:
                print("服务器返回错误详情:")
                print(json.dumps(e.response.json(), indent=2, ensure_ascii=False))
            except:
                print(f"服务器返回原始内容: {e.response.text}")
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    main()