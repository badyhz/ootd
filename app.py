# -*- coding: utf-8 -*-
from flask import Flask, render_template, jsonify
import datetime
# 引入 timedelta 用于计算明天
from datetime import timedelta
import requests
import json
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ================= 环境变量配置 =================
TEST_APP_ID = os.environ.get("WX_APP_ID")
TEST_APP_SECRET = os.environ.get("WX_APP_SECRET")
TEMPLATE_ID = os.environ.get("WX_TEMPLATE_ID") # 【重要】记得换成新的模板ID
H5_URL = os.environ.get("WX_H5_URL")

_openids = os.environ.get("WX_USER_OPEN_IDS", "")
USER_OPEN_IDS = [oid.strip() for oid in _openids.split(",") if oid.strip()]
# ===============================================

# --- 核心五行算法 ---
EARTHLY_BRANCHES = ['亥', '子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌']
REF_DATE = datetime.date(2025, 10, 21) 
REF_INDEX = 0

# 新增：计算指定日期的运势（传入 target_date）
def get_fortune_by_date(target_date):
    delta = (target_date - REF_DATE).days
    current_index = (REF_INDEX + delta) % 12
    if current_index < 0: current_index += 12
    branch = EARTHLY_BRANCHES[current_index]
    
    # 1. 定义色盘
    C = {
        'green_cyan': '绿色 & 青色',
        'black_blue': '黑色 & 深蓝',
        'yellow_caramel': '黄色 & 焦糖',
        'white_silver': '白色 & 银色',
        'red_purple': '红色 & 紫色',
        'red_pink': '红色 & 粉色',
        'gold_light': '金色 & 浅色',
        'black': '黑色', 'green': '绿色', 'white': '白色', 'yellow': '黄色'
    }

    # 2. 定义十二神 (值符)
    DUTY_MAP = {
        '亥': '福德', '子': '白虎', '丑': '龙德', '寅': '吊客', 
        '卯': '病符', '辰': '值符', '巳': '太阳', '午': '伤符', 
        '未': '太阴', '申': '官符', '酉': '死符', '戌': '破碎'
    }

    # 3. 每日运势映射 [元素, 大吉, 次吉, 招财, 较累, 不宜]
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
    duty_god = DUTY_MAP.get(branch, "")
    
    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "branch": f"{branch} · {data[0]}", # 例如：亥 · 水
        "duty": duty_god,                   # 新增：福德
        "best": data[1],
        "secondary": data[2],
        "wealth": data[3],
        "tired": data[4],
        "avoid": data[5]
    }

# --- 微信发送逻辑 ---
def get_token():
    if not TEST_APP_ID or not TEST_APP_SECRET:
        return None, "环境变量未配置"
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={TEST_APP_ID}&secret={TEST_APP_SECRET}"
    try:
        resp = requests.get(url, verify=False).json()
        if 'access_token' in resp:
            return resp['access_token'], None
        else:
            return None, f"微信接口报错: {json.dumps(resp)}"
    except Exception as e:
        return None, str(e)

def send_push():
    token, error = get_token()
    if not token: return f"Token获取失败: {error}"
    
    # 【关键修改】计算明天的日期
    tomorrow = datetime.date.today() + timedelta(days=1)
    # 获取明天的运势
    fortune = get_fortune_by_date(tomorrow)
    
    # 构造数据包 (新增了 duty 字段)
    data_payload = {
        "template_id": TEMPLATE_ID,
        "url": H5_URL,
        "data": {
            # 在日期后面加个(明日)的提示，更人性化
            "date": {"value": f"{fortune['date']} (明天)", "color": "#666666"},
            "branch": {"value": fortune['branch'], "color": "#173177"},
            "duty": {"value": fortune['duty'], "color": "#E65100"},        # 新增：值神 (橙色高亮)
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
            res = requests.post(url, json=data_payload, verify=False).json()
            results.append(res)
        except Exception as e:
            results.append(str(e))
        
    return str(results)

# --- 路由 ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/daily_push')
def trigger_push():
    res = send_push()
    return jsonify({"status": "done", "result": res})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
