# -*- coding: utf-8 -*-
from flask import Flask, render_template, jsonify
import datetime
import requests
import json
import os

app = Flask(__name__)

# ================= 环境变量配置 =================
# 这些值配置在微信云托管后台，代码里不写死，GitHub 上就不会泄露
TEST_APP_ID = os.environ.get("WX_APP_ID")
TEST_APP_SECRET = os.environ.get("WX_APP_SECRET")
TEMPLATE_ID = os.environ.get("WX_TEMPLATE_ID") 
H5_URL = os.environ.get("WX_H5_URL")

# 处理接收者 OpenID (支持多人，云托管后台用逗号隔开填入)
_openids = os.environ.get("WX_USER_OPEN_IDS", "")
USER_OPEN_IDS = [oid.strip() for oid in _openids.split(",") if oid.strip()]
# ===============================================

# --- 核心五行算法 (计算 5 种状态) ---
EARTHLY_BRANCHES = ['亥', '子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌']
REF_DATE = datetime.date(2025, 10, 21) 
REF_INDEX = 0

def get_today_fortune():
    today = datetime.date.today()
    delta = (today - REF_DATE).days
    current_index = (REF_INDEX + delta) % 12
    if current_index < 0: current_index += 12
    branch = EARTHLY_BRANCHES[current_index]
    
    # 定义色盘
    C = {
        'green_cyan': '绿色 & 青色',
        'black_blue': '黑色 & 深蓝',
        'yellow_caramel': '黄色 & 焦糖',
        'white_silver': '白色 & 银色',
        'red_purple': '红色 & 紫色',
        'red_pink': '红色 & 粉色',
        'gold_light': '金色 & 浅色',
        'black': '黑色',
        'green': '绿色',
        'white': '白色',
        'yellow': '黄色'
    }

    # 每日运势映射: [元素, 大吉, 次吉, 招财, 较累, 不宜]
    mapping = {
        '亥': ['水', C['green_cyan'], C['black_blue'], C['yellow_caramel'], C['white_silver'], C['red_purple']],
        '子': ['水', C['green_cyan'], C['black_blue'], C['yellow_caramel'], C['white_silver'], C['red_purple']],
        '丑': ['土', C['white_silver'], C['yellow_caramel'], C['green_cyan'], C['red_pink'], C['black_blue']],
        '寅': ['木', C['red_purple'], C['green_cyan'], C['gold_light'], C['black_blue'], C['yellow']],
        '卯': ['木', C['red_purple'], C['green_cyan'], C['gold_light'], C['black_blue'], C['yellow']],
        '辰': ['土', C['white_silver'], C['yellow_caramel'], C['green_cyan'], C['red_pink'], C['black_blue']],
        '巳': ['火', C['yellow_caramel'], C['red_purple'], C['black'], C['green'], C['white']],
        '午': ['火', C['yellow_caramel'], C['red_purple'], C['black'], C['green'], C['white']],
        '未': ['土', C['white_silver'], C['yellow_caramel'], C['green_cyan'], C['red_pink'], C['black_blue']],
        '申': ['金', C['black_blue'], C['white_silver'], C['red_pink'], C['yellow_caramel'], C['green_cyan']],
        '酉': ['金', C['black_blue'], C['white_silver'], C['red_pink'], C['yellow_caramel'], C['green_cyan']],
        '戌': ['土', C['white_silver'], C['yellow_caramel'], C['green_cyan'], C['red_pink'], C['black_blue']],
    }
    
    data = mapping.get(branch)
    
    return {
        "date": today.strftime("%Y-%m-%d"),
        "branch": f"{branch} · {data[0]}日",
        "best": data[1],
        "secondary": data[2],
        "wealth": data[3],
        "tired": data[4],
        "avoid": data[5]
    }

# --- 微信发送逻辑 ---
def get_token():
    if not TEST_APP_ID or not TEST_APP_SECRET:
        print("错误: 环境变量未配置")
        return None

    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={TEST_APP_ID}&secret={TEST_APP_SECRET}"
    try:
        resp = requests.get(url).json()
        return resp.get('access_token')
    except Exception as e:
        print(f"Token error: {e}")
        return None

def send_push():
    token = get_token()
    if not token: return "Token获取失败"
    
    fortune = get_today_fortune()
    
    # 构造数据包 (对应模板里的 {{key.DATA}})
    data_payload = {
        "template_id": TEMPLATE_ID,
        "url": H5_URL,
        "data": {
            "date": {"value": fortune['date'], "color": "#666666"},
            "branch": {"value": fortune['branch'], "color": "#173177"},
            "best": {"value": fortune['best'], "color": "#2e7d32"},       
            "secondary": {"value": fortune['secondary'], "color": "#1976D2"}, 
            "wealth": {"value": fortune['wealth'], "color": "#F57F17"},   
            "tired": {"value": fortune['tired'], "color": "#9C27B0"},     
            "avoid": {"value": fortune['avoid'], "color": "#c62828"}      
        }
    }
    
    results = []
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    
    if not USER_OPEN_IDS:
        return "未设置接收者OpenID"

    for openid in USER_OPEN_IDS:
        data_payload["touser"] = openid
        try:
            res = requests.post(url, json=data_payload).json()
            results.append(res)
        except Exception as e:
            results.append(str(e))
        
    return str(results)

# --- 路由 ---
@app.route('/')
def index():
    # 这一句保证了 H5 依然能正常访问！
    return render_template('index.html')

@app.route('/daily_push')
def trigger_push():
    res = send_push()
    return jsonify({"status": "done", "result": res})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
