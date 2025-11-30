# -*- coding: utf-8 -*-
from flask import Flask, render_template
import datetime
import requests
import json
import os

app = Flask(__name__)

# ================= 配置区域 =================
# 请填入你的公众号 AppID 和 AppSecret
# (建议使用微信云托管的环境变量，但为了简单，先填在这里，注意不要泄露给别人)
APP_ID = "你的APP_ID"  
APP_SECRET = "你的APP_SECRET"
# 你的微信号（用于测试接口），或者留空
USER_OPENID = "" 
# ===========================================

# --- 五行算法 (与前端HTML保持绝对一致) ---
EARTHLY_BRANCHES = ['亥', '子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌']
REF_DATE = datetime.date(2025, 10, 21) # 2025-10-21 是亥日
REF_INDEX = 0

def get_today_fortune():
    today = datetime.date.today()
    delta = (today - REF_DATE).days
    current_index = (REF_INDEX + delta) % 12
    # 处理负数取模
    if current_index < 0:
        current_index += 12
        
    branch = EARTHLY_BRANCHES[current_index]
    
    # 简单的五行对应 (仅用于推送摘要)
    branch_map = {
        '亥': {'e': '水', 'best': '绿色 & 青色'},
        '子': {'e': '水', 'best': '绿色 & 青色'},
        '丑': {'e': '土', 'best': '白色 & 银色'},
        '寅': {'e': '木', 'best': '红色 & 粉紫'},
        '卯': {'e': '木', 'best': '红色 & 粉紫'},
        '辰': {'e': '土', 'best': '白色 & 银色'},
        '巳': {'e': '火', 'best': '黄色 & 焦糖'},
        '午': {'e': '火', 'best': '黄色 & 焦糖'},
        '未': {'e': '土', 'best': '白色 & 银色'},
        '申': {'e': '金', 'best': '黑色 & 深蓝'},
        '酉': {'e': '金', 'best': '黑色 & 深蓝'},
        '戌': {'e': '土', 'best': '白色 & 银色'},
    }
    
    info = branch_map.get(branch, {'e': '未知', 'best': '未知'})
    
    return {
        "date": today.strftime("%Y-%m-%d"),
        "branch": branch,
        "element": info['e'],
        "best": info['best']
    }

# --- 微信发送逻辑 ---
def get_access_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
    try:
        resp = requests.get(url).json()
        return resp.get('access_token')
    except Exception as e:
        print(f"Token error: {e}")
        return None

def send_wechat_msg():
    token = get_access_token()
    if not token:
        return "获取 Token 失败"
        
    fortune = get_today_fortune()
    
    # 推送内容
    msg_content = f"""📅 {fortune['date']} 穿衣指南

今日：{fortune['branch']} ({fortune['element']})
✨ 大吉色：{fortune['best']}

(点击菜单栏“今日指南”查看详细色卡)
"""
    
    # 这里演示发送给特定用户 (客服接口)，实际运营建议使用“模板消息”
    # 如果没有 USER_OPENID，这里只是打印日志
    if not USER_OPENID:
        print("未设置接收者 OpenID，仅打印内容：")
        print(msg_content)
        return "未设置 OpenID，查看日志"

    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
    data = {
        "touser": USER_OPENID,
        "msgtype": "text",
        "text": {
            "content": msg_content
        }
    }
    
    resp = requests.post(url, json=data)
    return resp.text

# --- 路由 ---

@app.route('/')
def index():
    # 访问首页时，显示你的 H5
    return render_template('index.html')

@app.route('/trigger_push')
def trigger():
    # 这是一个手动触发推送的开关，访问这个网址就会发消息
    res = send_wechat_msg()
    return f"推送结果: {res}"

if __name__ == '__main__':
    # 监听 80 端口
    app.run(host='0.0.0.0', port=80)