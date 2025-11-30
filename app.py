# -*- coding: utf-8 -*-
from flask import Flask, render_template, jsonify
import datetime
import requests
import json
import os

app = Flask(__name__)

# --- 环境变量 ---
TEST_APP_ID = os.environ.get("WX_APP_ID")
TEST_APP_SECRET = os.environ.get("WX_APP_SECRET")
TEMPLATE_ID = os.environ.get("WX_TEMPLATE_ID") 
H5_URL = os.environ.get("WX_H5_URL")
_openids = os.environ.get("WX_USER_OPEN_IDS", "")
USER_OPEN_IDS = [oid.strip() for oid in _openids.split(",") if oid.strip()]

# --- 简单算法 ---
def get_today_fortune():
    return {
        "date": datetime.date.today().strftime("%Y-%m-%d"),
        "branch": "测试 · 调试中",
        "best": "调试绿色",
        "secondary": "调试蓝色",
        "wealth": "调试金色",
        "tired": "调试紫色",
        "avoid": "调试红色"
    }

# --- 调试版微信发送逻辑 ---
def get_token():
    # 1. 检查环境变量
    if not TEST_APP_ID:
        return None, "错误：WX_APP_ID 环境变量未读取到！请检查云托管后台是否配置，或是否点击了'更新服务'。"
    if not TEST_APP_SECRET:
        return None, "错误：WX_APP_SECRET 环境变量未读取到！"

    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={TEST_APP_ID}&secret={TEST_APP_SECRET}"
    try:
        resp = requests.get(url).json()
        if 'access_token' in resp:
            return resp['access_token'], None
        else:
            # 2. 这里的报错最关键！
            return None, f"微信接口拒绝了请求，原因: {json.dumps(resp, ensure_ascii=False)}"
    except Exception as e:
        return None, f"网络请求炸了: {str(e)}"

def send_push():
    token, error = get_token()
    if not token: return f"【Token获取失败】原因 -> {error}"
    
    # ... 省略中间构造数据的代码，为了调试先只看 Token ...
    return f"Token获取成功！是: {token[:10]}... 接下来请检查 OpenID 配置"

# --- 路由 ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/daily_push')
def trigger_push():
    res = send_push()
    # 把结果直接显示在网页上
    return jsonify({"调试结果": res})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
