# -*- coding: utf-8 -*-
from flask import Flask, render_template_string, jsonify
import datetime
from datetime import timedelta
import requests
import json
import os
import urllib3

# 禁用 SSL 警告 (用于绕过云托管环境证书问题)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ================= 环境变量配置 =================
# 请在微信云托管后台 -> 服务设置 -> 环境变量 中填写这些值
TEST_APP_ID = os.environ.get("WX_APP_ID")
TEST_APP_SECRET = os.environ.get("WX_APP_SECRET")
# 模板 ID (包含7个字段: date, branch, duty, best, secondary, wealth, tired, avoid)
TEMPLATE_ID = os.environ.get("WX_TEMPLATE_ID") 
H5_URL = os.environ.get("WX_H5_URL")

# 接收者 OpenID (支持多个，逗号隔开)
_openids = os.environ.get("WX_USER_OPEN_IDS", "")
USER_OPEN_IDS = [oid.strip() for oid in _openids.split(",") if oid.strip()]
# ===============================================

# --- 核心五行算法 ---
EARTHLY_BRANCHES = ['亥', '子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌']
REF_DATE = datetime.date(2025, 10, 21) # 2025-10-21 是亥日
REF_INDEX = 0

def get_fortune_by_date(target_date):
    """根据日期计算运势"""
    delta = (target_date - REF_DATE).days
    current_index = (REF_INDEX + delta) % 12
    if current_index < 0: current_index += 12
    branch = EARTHLY_BRANCHES[current_index]
    
    # 1. 定义色盘 (标准五行色)
    C = {
        'green_cyan': '青色 & 绿色',
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
        "branch": f"{branch} · {data[0]}", 
        "duty": duty_god,
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
        # verify=False 绕过证书验证
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
    
    # 计算明天
    tomorrow = datetime.date.today() + timedelta(days=1)
    fortune = get_fortune_by_date(tomorrow)
    
    # 构造数据包
    data_payload = {
        "template_id": TEMPLATE_ID,
        "url": H5_URL,
        "data": {
            "date": {"value": f"{fortune['date']} (明天)", "color": "#666666"},
            "branch": {"value": fortune['branch'], "color": "#173177"},
            "duty": {"value": fortune['duty'], "color": "#E65100"},
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

# --- HTML 模板内容 ---
# 将 index.html 的内容内嵌在这里，方便单文件部署
HTML_CONTENT = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>五行衣橱 OOTD</title>
    <style>
        :root {
            --glass-bg: rgba(255, 255, 255, 0.65);
            --glass-border: rgba(255, 255, 255, 0.4);
            --text-primary: #1d1d1f;
            --text-secondary: #86868b;
            --font-main: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", sans-serif;
            --theme-gradient-1: #ff9a9e;
            --theme-gradient-2: #fecfef;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { font-family: var(--font-main); background: #f5f5f7; color: var(--text-primary); min-height: 100vh; padding-bottom: 30px; }
        
        .ambient-bg { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: linear-gradient(135deg, var(--theme-gradient-1), var(--theme-gradient-2), #fff0f0); background-size: 400% 400%; z-index: -1; animation: gradientMove 15s ease infinite; }
        @keyframes gradientMove { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }

        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        
        /* Header */
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-top: env(safe-area-inset-top); }
        .brand { font-size: 14px; font-weight: 600; letter-spacing: 2px; color: var(--text-secondary); }
        
        /* Date Picker */
        .date-picker-wrapper { background: rgba(255,255,255,0.5); padding: 4px 10px; border-radius: 20px; display: flex; align-items: center; margin-left: 10px; backdrop-filter: blur(5px); }
        #datePicker { border: none; background: transparent; font-family: var(--font-main); font-size: 14px; font-weight: 600; width: 110px; outline: none; }

        /* Hero */
        .hero-section { text-align: center; margin-bottom: 25px; }
        .hero-title { font-size: 13px; font-weight: 500; color: var(--text-secondary); letter-spacing: 1px; }
        .hero-main-text { font-size: 28px; font-weight: 800; margin: 5px 0; background: linear-gradient(45deg, #1d1d1f, #4a4a4a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .duty-badge { display: inline-block; padding: 2px 8px; background: rgba(0,0,0,0.05); border-radius: 8px; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 5px; }

        /* Tabs */
        .tabs { display: flex; background: rgba(255, 255, 255, 0.4); padding: 3px; border-radius: 14px; margin-bottom: 20px; }
        .tab-btn { flex: 1; padding: 8px; border: none; background: transparent; font-size: 13px; font-weight: 600; color: var(--text-secondary); border-radius: 11px; cursor: pointer; transition: all 0.3s; }
        .tab-btn.active { background: #fff; color: #000; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }

        /* Cards */
        .glass-card { background: var(--glass-bg); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid var(--glass-border); border-radius: 20px; padding: 20px; margin-bottom: 15px; box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.05); }
        
        .outfit-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
        .grid-item { position: relative; overflow: hidden; min-height: 140px; display: flex; flex-direction: column; justify-content: space-between; }
        .grid-item.large { grid-column: span 2; min-height: 160px; background: linear-gradient(135deg, rgba(255,255,255,0.8), rgba(255,255,255,0.4)); }
        
        .tag { font-size: 10px; font-weight: 700; text-transform: uppercase; opacity: 0.6; margin-bottom: 5px; }
        .color-name { font-size: 20px; font-weight: 700; margin-bottom: 4px; line-height: 1.2; }
        .color-meaning { font-size: 12px; opacity: 0.7; }
        .color-blob { position: absolute; right: -20px; bottom: -20px; width: 100px; height: 100px; border-radius: 50%; filter: blur(25px); opacity: 0.8; }

        /* Forecast List */
        .forecast-item { display: flex; flex-direction: column; padding: 15px; border-radius: 16px; background: rgba(255,255,255,0.5); border: 1px solid rgba(255,255,255,0.3); gap: 8px; margin-bottom: 10px; }
        .forecast-header { display: flex; justify-content: space-between; font-size: 14px; font-weight: 700; }
        .forecast-row { display: flex; justify-content: space-between; align-items: center; font-size: 12px; }
        .dot { width: 12px; height: 12px; border-radius: 50%; margin-left: 6px; display: inline-block; }

        .tab-panel { display: none; animation: fadeIn 0.3s ease; }
        .tab-panel.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
        
        footer { text-align: center; font-size: 11px; color: #999; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="ambient-bg"></div>
    <div class="container">
        <header>
            <div class="brand">DAILY CHIC · 五行</div>
            <div class="date-picker-wrapper">
                <input type="date" id="datePicker">
            </div>
        </header>

        <section class="hero-section">
            <div class="hero-title" id="heroLabel">今日气场</div>
            <div class="hero-main-text" id="elementTitle">...</div>
            <div class="duty-badge" id="dutyBadge">...</div>
            <div class="hero-sub" id="luckyNote">Align your energy</div>
        </section>

        <div class="tabs">
            <button class="tab-btn active" id="tabToday" onclick="switchTab('today')">今日指南</button>
            <button class="tab-btn" onclick="switchTab('tomorrow')">次日预告</button>
            <button class="tab-btn" onclick="switchTab('forecast')">未来走势</button>
        </div>

        <div id="today" class="tab-panel active"><div id="todayContent" class="outfit-grid"></div></div>
        <div id="tomorrow" class="tab-panel"><div id="tomorrowContent" class="outfit-grid"></div></div>
        <div id="forecast" class="tab-panel"><div class="glass-card"><div style="margin-bottom:15px;font-weight:600;">未来三天</div><div id="forecastContainer"></div></div></div>

        <footer>Inspired by Traditional Wisdom</footer>
    </div>

    <script>
        // === 纯净数据源 (Python同步) ===
        const COLORS = {
            green_cyan: { name: '青色 & 绿色', hex: 'linear-gradient(135deg, #4CAF50, #00BCD4)' },
            black_blue: { name: '黑色 & 深蓝', hex: 'linear-gradient(135deg, #000000, #1565C0)' },
            yellow_caramel: { name: '黄色 & 焦糖', hex: 'linear-gradient(135deg, #FFC107, #795548)' },
            white_silver: { name: '白色 & 银色', hex: 'linear-gradient(135deg, #FFFFFF, #B0BEC5)' },
            red_purple: { name: '红色 & 紫色', hex: 'linear-gradient(135deg, #F44336, #9C27B0)' },
            red_pink: { name: '红色 & 粉色', hex: 'linear-gradient(135deg, #F44336, #E91E63)' },
            gold_light: { name: '金色 & 浅色', hex: 'linear-gradient(135deg, #FFD700, #F5F5F5)' },
            black: { name: '黑色', hex: 'linear-gradient(135deg, #000000, #424242)' },
            green: { name: '绿色', hex: 'linear-gradient(135deg, #4CAF50, #81C784)' },
            white: { name: '白色', hex: 'linear-gradient(135deg, #FFFFFF, #E0E0E0)' },
            yellow: { name: '黄色', hex: 'linear-gradient(135deg, #FFEB3B, #FBC02D)' }
        };

        const DATA = {
            '亥': { e:'水', duty:'福德', theme:['#a1c4fd','#c2e9fb'], best:COLORS.green_cyan, sec:COLORS.black_blue, wealth:COLORS.yellow_caramel, tired:COLORS.white_silver, avoid:COLORS.red_purple },
            '子': { e:'水', duty:'白虎', theme:['#accbee','#e7f0fd'], best:COLORS.green_cyan, sec:COLORS.black_blue, wealth:COLORS.yellow_caramel, tired:COLORS.white_silver, avoid:COLORS.red_purple },
            '丑': { e:'土', duty:'龙德', theme:['#e6dee9','#dad4ec'], best:COLORS.white_silver, sec:COLORS.yellow_caramel, wealth:COLORS.green_cyan, tired:COLORS.red_pink, avoid:COLORS.black_blue },
            '寅': { e:'木', duty:'吊客', theme:['#d4fc79','#96e6a1'], best:COLORS.red_purple, sec:COLORS.green_cyan, wealth:COLORS.gold_light, tired:COLORS.black_blue, avoid:COLORS.yellow },
            '卯': { e:'木', duty:'病符', theme:['#84fab0','#8fd3f4'], best:COLORS.red_purple, sec:COLORS.green_cyan, wealth:COLORS.gold_light, tired:COLORS.black_blue, avoid:COLORS.yellow },
            '辰': { e:'土', duty:'值符', theme:['#fdfbfb','#ebedee'], best:COLORS.white_silver, sec:COLORS.yellow_caramel, wealth:COLORS.green_cyan, tired:COLORS.red_pink, avoid:COLORS.black_blue },
            '巳': { e:'火', duty:'太阳', theme:['#fa709a','#fee140'], best:COLORS.yellow_caramel, sec:COLORS.red_purple, wealth:COLORS.black, tired:COLORS.green, avoid:COLORS.white },
            '午': { e:'火', duty:'伤符', theme:['#ff9a9e','#fecfef'], best:COLORS.yellow_caramel, sec:COLORS.red_purple, wealth:COLORS.black, tired:COLORS.green, avoid:COLORS.white },
            '未': { e:'土', duty:'太阴', theme:['#a18cd1','#fbc2eb'], best:COLORS.white_silver, sec:COLORS.yellow_caramel, wealth:COLORS.green_cyan, tired:COLORS.red_pink, avoid:COLORS.black_blue },
            '申': { e:'金', duty:'官符', theme:['#e0c3fc','#8ec5fc'], best:COLORS.black_blue, sec:COLORS.white_silver, wealth:COLORS.red_pink, tired:COLORS.yellow_caramel, avoid:COLORS.green_cyan },
            '酉': { e:'金', duty:'死符', theme:['#cfd9df','#e2ebf0'], best:COLORS.black_blue, sec:COLORS.white_silver, wealth:COLORS.red_pink, tired:COLORS.yellow_caramel, avoid:COLORS.green_cyan },
            '戌': { e:'土', duty:'破碎', theme:['#fccb90','#d57eeb'], best:COLORS.white_silver, sec:COLORS.yellow_caramel, wealth:COLORS.green_cyan, tired:COLORS.red_pink, avoid:COLORS.black_blue }
        };

        const BRANCHES = ['亥','子','丑','寅','卯','辰','巳','午','未','申','酉','戌'];
        const REF_DATE = new Date('2025-10-21T00:00:00'); // 亥日

        let selectedDate = new Date();
        let currentTab = 'today';

        function getBranch(date) {
            const diff = Math.floor((date - REF_DATE) / 86400000);
            const idx = ((diff % 12) + 12) % 12;
            return { name: BRANCHES[idx], ...DATA[BRANCHES[idx]] };
        }

        function formatDate(d) { return d.toISOString().split('T')[0]; }
        function formatShort(d) { return `${d.getMonth()+1}.${d.getDate()}`; }

        function renderGrid(containerId, info) {
            const html = `
                <div class="glass-card grid-item large">
                    <div><div class="tag" style="color:#2e7d32">大吉 · 环境生我</div><div class="color-name">${info.best.name}</div><div class="color-meaning">办事易成，开心轻松</div></div>
                    <div class="color-blob" style="background:${info.best.hex}"></div>
                </div>
                <div class="glass-card grid-item">
                    <div><div class="tag">次吉 · 比肩</div><div class="color-name" style="font-size:16px">${info.sec.name}</div><div class="color-meaning">合作共赢</div></div>
                    <div class="color-blob" style="background:${info.sec.hex}"></div>
                </div>
                <div class="glass-card grid-item">
                    <div><div class="tag" style="color:#F57F17">招财 · 我克环境</div><div class="color-name" style="font-size:16px">${info.wealth.name}</div><div class="color-meaning">辛苦有得</div></div>
                    <div class="color-blob" style="background:${info.wealth.hex}"></div>
                </div>
                <div class="glass-card grid-item large" style="min-height:100px; display:flex; flex-direction:row; gap:10px;">
                    <div style="flex:1">
                        <div class="tag" style="color:#9C27B0">较累 · 我生环境</div>
                        <div style="font-size:14px;font-weight:700">${info.tired.name}</div>
                    </div>
                    <div style="width:1px;background:#eee"></div>
                    <div style="flex:1">
                        <div class="tag" style="color:#c62828">不宜 · 环境克我</div>
                        <div style="font-size:14px;font-weight:700">${info.avoid.name}</div>
                    </div>
                </div>
            `;
            document.getElementById(containerId).innerHTML = html;
        }

        function renderForecast(baseDate) {
            let html = '';
            for(let i=1; i<=3; i++) {
                const d = new Date(baseDate); d.setDate(baseDate.getDate() + i);
                const info = getBranch(d);
                html += `
                    <div class="forecast-item">
                        <div class="forecast-header"><span>${formatShort(d)}</span> <span>${info.name} · ${info.e}</span></div>
                        <div class="forecast-row"><span style="color:#2e7d32">大吉</span> <div>${info.best.name}<span class="dot" style="background:${info.best.hex}"></span></div></div>
                        <div class="forecast-row"><span style="color:#555">次吉</span> <div>${info.sec.name}<span class="dot" style="background:${info.sec.hex}"></span></div></div>
                        <div class="forecast-row"><span style="color:#F57F17">招财</span> <div>${info.wealth.name}<span class="dot" style="background:${info.wealth.hex}"></span></div></div>
                    </div>
                `;
            }
            document.getElementById('forecastContainer').innerHTML = html;
        }

        function updateUI() {
            const picker = document.getElementById('datePicker');
            if (document.activeElement !== picker) picker.value = formatDate(selectedDate);

            // Calculate dates
            const today = new Date(selectedDate);
            const tomorrow = new Date(selectedDate); tomorrow.setDate(today.getDate() + 1);
            
            // Hero Logic
            const heroDate = currentTab === 'tomorrow' ? tomorrow : today;
            const heroInfo = getBranch(heroDate);
            
            document.documentElement.style.setProperty('--theme-gradient-1', heroInfo.theme[0]);
            document.documentElement.style.setProperty('--theme-gradient-2', heroInfo.theme[1]);
            
            document.getElementById('elementTitle').innerText = `${heroInfo.name} · ${heroInfo.e}`;
            document.getElementById('elementTitle').style.backgroundImage = heroInfo.best.hex;
            document.getElementById('dutyBadge').innerText = `值神 · ${heroInfo.duty}`;
            document.getElementById('heroLabel').innerText = currentTab === 'tomorrow' ? '明日气场' : '今日气场';
            document.getElementById('tabToday').innerText = `今日 ${formatShort(today)}`;

            renderGrid('todayContent', getBranch(today));
            renderGrid('tomorrowContent', getBranch(tomorrow));
            renderForecast(today);
        }

        window.switchTab = function(tab) {
            currentTab = tab;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            document.getElementById(tab).classList.add('active');
            updateUI();
        }

        document.getElementById('datePicker').addEventListener('change', (e) => {
            selectedDate = new Date(e.target.value);
            updateUI();
        });

        // Init
        updateUI();
    </script>
</body>
</html>
"""

# --- 路由 ---
@app.route('/')
def index():
    return render_template_string(HTML_CONTENT)

@app.route('/daily_push')
def trigger_push():
    res = send_push()
    return jsonify({"status": "done", "result": res})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
