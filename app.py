import streamlit as st
import google.generativeai as genai
import os
import re
import time
import random
from dotenv import load_dotenv

# 載入環境變數 (.env)
load_dotenv()

# ==========================================
# 1. 頁面配置與高級樣式
# ==========================================
st.set_page_config(
    page_title="AI 奧勒岡 2v2 雙人辯論模擬器",
    page_icon="🏛️",
    layout="wide"
)

# 注入 CSS 提升介面視覺效果 (美觀的卡片、漸層、自訂對話框顏色)
st.markdown("""
<style>
    /* 調整背景與漸層標題 */
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #3b82f6, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
        text-align: center;
    }
    .sub-title {
        font-size: 1.1rem;
        color: #94a3b8;
        text-align: center;
        margin-bottom: 25px;
    }
    
    /* 左右面板的美化區塊 */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
    }
    
    /* 辯士類型專屬色彩樣式 */
    .role-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .badge-rational { background-color: #1e3a8a; color: #60a5fa; }
    .badge-emotional { background-color: #701a75; color: #f472b6; }
    .badge-conservative { background-color: #064e3b; color: #34d399; }
    .badge-reformist { background-color: #4c1d95; color: #c084fc; }
    .badge-moderator { background-color: #3f3f46; color: #d4d4d8; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 工具函式與內建資料
# ==========================================
# 預設題目的立場主張庫 (確保 AI 明白 正反方 立場)
DEFAULT_STANCES = {
    "為了社會穩定，能否犧牲部分自由？": {
        "pro": "為維持社會秩序與穩定，必要時應限制或合理犧牲個體的部分自由。",
        "con": "自由是基本尊嚴與人權之本，絕不能以維持穩定為名進行妥協或犧牲。"
    },
    "極端言論是否也應被保障？": {
        "pro": "極端言論亦屬於言論自由範疇，應受到程序正義保障，以防公權力假借審查工具任意打壓異議。",
        "con": "極端言論若煽動仇恨或實質暴力，將侵犯他人生存尊嚴，社會不應賦予其絕對免責權。"
    },
    "道德是否只是社會建構？": {
        "pro": "道德純粹是由文化、制度與歷史集體共識所形塑的社會契約與人造產物，不存在客觀真理性。",
        "con": "道德不只是社會建構，它奠基於生物演化利他本能、人類同理心或客觀理性思維的普遍基礎。"
    },
    "是否廢除死刑？": {
        "pro": "支持廢除死刑，以保障生命權、防範不可挽回的司法冤獄，並避免國家公權力侵犯生存權。",
        "con": "反對廢除死刑，死刑能體現罪刑相當的司法正義，並給予重大犯罪者實質懲戒，撫慰受害者家屬。"
    },
    "人工智慧是否應擁有法律人格？": {
        "pro": "AI 應擁有法律人格，以便明確規範其在法律上的權責歸屬，並解決未來因自主決策產生的法律糾紛。",
        "con": "AI 不應擁有法律人格，AI 僅是程式與工具，賦予其人格會免除人類監管者的責任，導致倫理失序。"
    },
    "AI統治世界會比人類更好嗎？": {
        "pro": "AI 統治世界會更好，因為 AI 能杜絕貪婪、自私與偏見，依據數據做出絕對理性的全域最優決策。",
        "con": "AI 統治世界不會更好，因為 AI 缺乏感性同理、溫度與人性彈性，且算法容易固化既存不平等偏見。"
    },
    "如果能上傳意識，人類還算活著嗎？": {
        "pro": "上傳意識後依然活著，因為人類生命的本質是心智運作、記憶與自我意識流，而非侷限於碳基肉身。",
        "con": "上傳意識後不算活著，人類生命包含生物感知、必死性與肉身侷限，純數字代碼的模擬僅是沒有靈魂的複製品。"
    },
    "人是否其實只愛自己？": {
        "pro": "人的所有行為本質上皆出於利己動機，即使是看似無私的奉獻，亦是為了滿足自我的道德感與心靈安寧。",
        "con": "人並非只愛自己，人類具備真正的利他天性與無私之愛，能在特定情況下做出純粹且不求回報的犧牲。"
    },
    "「成熟」是不是對熱情的妥協？": {
        "pro": "成熟即是對幼稚熱情的妥協，是認清社會規範與現實限制後，選擇穩定、合理生活方式的必然妥協。",
        "con": "成熟並非妥協，而是學會用更成熟、更具建設性且可持續的手段，去落實與呵護心中的真實熱情。"
    },
    "幸福比真相更重要嗎？": {
        "pro": "幸福比真相更重要，真相往往殘酷且無濟於事，人生的終極價值在於體驗平靜、美好與幸福感。",
        "con": "真相比幸福更重要，虛假的幸福是空洞的自我欺騙，唯有正視真相，人類尊嚴與獨立人格才具備意義。"
    },
    "強者是否有資格制定規則？": {
        "pro": "從歷史演進與現實主義角度看，強者必然且有資格制定規則，以維護集體秩序並推動社會運作。",
        "con": "強者無權制定規則，規則應奠基於公平、正義與弱勢保障之上，強者強加的規則僅是壓迫的偽裝。"
    },
    "真誠是否其實很殘酷？": {
        "pro": "真誠往往伴隨赤裸且未經修飾的殘忍事實，會戳破虛假的美好泡泡，因此其本質是非常殘酷的。",
        "con": "真誠並非殘酷，它是建立深刻信任、長期健康關係的基石，虛偽的善意與欺騙才是最深層的傷害。"
    }
}

def find_file(filename: str) -> str:
    """智慧搜尋檔案路徑，支援根目錄與子目錄"""
    possible_paths = [
        os.path.join(".", "角色卡與辯題", filename),
        os.path.join("..", "角色卡與辯題", filename),
        os.path.join(".", filename),
        os.path.join("AI_Debate_NSYSU-main", "角色卡與辯題", filename),
        os.path.join(".", "AI_Debate_NSYSU-main", "角色卡與辯題", filename)
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def parse_topics(file_path: str) -> dict:
    """解析 議題.md 檔案並分組歸類"""
    categories = {}
    if not file_path or not os.path.exists(file_path):
        return {"哲學與社會": ["為了社會穩定，能否犧牲部分自由？"]}
    
    current_category = "未分類"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    current_category = line.lstrip("#").strip()
                    categories[current_category] = []
                elif line.startswith("-"):
                    topic = line.lstrip("-").strip()
                    if current_category not in categories:
                        categories[current_category] = []
                    categories[current_category].append(topic)
    except Exception as e:
        st.warning(f"解析議題檔錯誤: {e}")
        return {"預設": ["為了社會穩定，能否犧牲部分自由？"]}
    
    return categories if categories else {"預設": ["為了社會穩定，能否犧牲部分自由？"]}

def load_card_from_file(filename: str, base_instruction: str) -> str:
    """載入角色卡 Markdown 檔案內容，並附加基礎指令"""
    filepath = find_file(filename)
    if filepath and os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                file_content = f.read().strip()
            return f"{base_instruction}\n\n詳細角色設定：\n{file_content}"
        except Exception as e:
            return base_instruction
    return base_instruction

def clean_output(raw_text: str) -> str:
    """過濾 Gemma 4 產生的 <think> 標籤與不必要開場白"""
    # 移除 <think>...</think> 區塊 (包含跨行)
    cleaned_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL)
    # 移除常犯的 AI 發言起頭詞
    cleaned_text = re.sub(r'^(好的，|我的發言是：|以下是我的台詞：|我的發言：|當前發言：)\s*', '', cleaned_text).strip()
    # 移除前後引號
    cleaned_text = re.sub(r'^「(.*)」$', r'\1', cleaned_text).strip()
    return cleaned_text

# ==========================================
# 3. 預設指令與角色設定
# ==========================================
BASE_INSTRUCTIONS = {
    "理性派": "你是一名冷靜、講求邏輯與數據的辯士。發言必須條理分明，善用因果推論，嚴禁使用煽情字眼。絕對禁止輸出任何 <think> 標籤或內部推理過程，請直接給出最終發言。",
    "感性派": "你是一名充滿同理心、關注人類情感與弱勢權益的辯士。發言必須具備感染力，善用修辭與價值觀詰問。絕對禁止輸出 any <think> 標籤或內部推理過程，請直接給出最終發言。",
    "保守派": "你是一名謹慎、重視傳統價值與既有秩序的辯士。發言應強調風險控制、穩定性與長期影響。絕對禁止輸出 any <think> 標籤或內部推理過程，請直接給出最終發言。",
    "改革派": "你是一名積極、主張變革與進步的辯士。發言應聚焦於問題解決、創新方案與未來願景。絕對禁止輸出 any <think> 標籤或內部推理過程，請直接給出最終發言。"
}

# ==========================================
# 4. 初始化 Session State (狀態管理)
# ==========================================
if "debate_started" not in st.session_state:
    st.session_state.debate_started = False
if "current_step" not in st.session_state:
    st.session_state.current_step = 0
if "debate_history" not in st.session_state:
    st.session_state.debate_history = []
if "flow_sheet" not in st.session_state:
    st.session_state.flow_sheet = "目前為開場階段，雙方尚未交鋒。"
if "paused" not in st.session_state:
    st.session_state.paused = False
if "selected_topic" not in st.session_state:
    st.session_state.selected_topic = ""
if "pro_1_personality" not in st.session_state:
    st.session_state.pro_1_personality = "理性派"
if "pro_2_personality" not in st.session_state:
    st.session_state.pro_2_personality = "改革派"
if "con_1_personality" not in st.session_state:
    st.session_state.con_1_personality = "感性派"
if "con_2_personality" not in st.session_state:
    st.session_state.con_2_personality = "保守派"

# ==========================================
# 5. 側邊欄設定
# ==========================================
st.sidebar.title("⚙️ 辯論系統設定")

# API 金鑰輸入
api_key_env = os.environ.get("GOOGLE_API_KEY", "")
api_key = st.sidebar.text_input("Gemini API 金鑰", value=api_key_env, type="password", help="請輸入您的 Google Gemini API Key。若不輸入將無法呼叫模型。")

# 模型選擇
model_name = st.sidebar.selectbox(
    "指定 LLM 模型",
    ["gemma-4-26b-a4b-it", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash"],
    index=0,
    help="gemma-4-26b-a4b-it 是原設計中具備原生推理能力的模型。如遇無法呼叫，可切換為 gemini-1.5-flash 測試。"
)

st.sidebar.markdown("---")
st.sidebar.subheader("👥 辯論角色人格配置")

auto_assign = st.sidebar.checkbox("自動根據議題優化分配 (預設規則)", value=True, help="啟用時，若題目包含「穩定」與「自由」，系統會動態將正方二辯設為「保守派」，反方二辯設為「改革派」。")

personalities_list = ["理性派", "感性派", "保守派", "改革派"]

# 議題檔載入
topics_dict = parse_topics(find_file("議題.md"))

# 為了防止重複觸發，當前命題需即時記錄
# 此處提供 category 與 topic 選擇
st.sidebar.markdown("---")
st.sidebar.subheader("⏱️ 速率與流程控制")
cooldown_delay = st.sidebar.slider("發言冷卻延遲 (秒)", min_value=2, max_value=20, value=10, help="每次 API 請求後的冷卻秒數，避免頻繁請求導致 API 被限制 (Rate Limit/Quota Exceeded)。")
autoplay = st.sidebar.checkbox("自動連續辯論 (Autoplay)", value=True, help="勾選時，系統將會自動依序呼叫各階段，不需手動點選下一步。")

# ==========================================
# 6. 主頁面：命題選擇與立場設定區
# ==========================================
st.markdown("<div class='main-title'>🏛️ AI 奧勒岡 2v2 雙人辯論模擬器</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>基於 Gemma 4 與 Gemini 的跨人格線性辯論沙盒</div>", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("🎯 選擇與配置辯論議題")
    
    # 類別選擇
    selected_cat = st.selectbox("議題領域分類", list(topics_dict.keys()))
    
    # 議題選擇
    topic_options = topics_dict[selected_cat]
    topic_options_extended = topic_options + ["📝 自訂其他議題"]
    
    selected_topic_choice = st.selectbox("選擇預設命題", topic_options_extended)
    
    if selected_topic_choice == "📝 自訂其他議題":
        custom_topic = st.text_input("輸入自訂的辯論命題", "人工智慧發展是否應該受到嚴格限制？")
        current_topic = custom_topic
    else:
        current_topic = selected_topic_choice
        
    st.session_state.selected_topic = current_topic
    st.markdown(f"**當前命題：**【{current_topic}】")
    st.markdown("</div>", unsafe_allow_html=True)

# 執行角色自動配置
if auto_assign:
    p1 = "理性派"
    c1 = "感性派"
    p2 = "改革派"
    c2 = "保守派"
    
    if current_topic and "穩定" in current_topic and "自由" in current_topic:
        p2 = "保守派"
        c2 = "改革派"
    
    st.session_state.pro_1_personality = p1
    st.session_state.pro_2_personality = p2
    st.session_state.con_1_personality = c1
    st.session_state.con_2_personality = c2
else:
    # 自訂分配
    # 此處在 col1 內直接讓用戶設定，側邊欄僅有 checkbox
    pass

# 立場主張顯示與設定區 (非常重要：避免 AI 混淆立場)
with col1:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("⚖️ 立場主張聲明 (可自由編輯)")
    
    # 查找預設立場
    default_pro = ""
    default_con = ""
    if current_topic in DEFAULT_STANCES:
        default_pro = DEFAULT_STANCES[current_topic]["pro"]
        default_con = DEFAULT_STANCES[current_topic]["con"]
    else:
        default_pro = f"支持【{current_topic}】的肯定立場，論證其合理成立之處。"
        default_con = f"反對【{current_topic}】的肯定立場，指出其盲點、代價或論證其不成立。"
        
    pro_stance = st.text_input("🟢 正方立場核心主張 (Pro Stance)", value=default_pro)
    con_stance = st.text_input("🔴 反方立場核心主張 (Con Stance)", value=default_con)
    st.markdown("</div>", unsafe_allow_html=True)

# 讀取角色設定並準備 CARDS 字典
CARDS = {}
for p in personalities_list:
    filename = f"{p}.md"
    CARDS[p] = load_card_from_file(filename, BASE_INSTRUCTIONS[p])

# 奧勒岡 2v2 線性流程定義
# side: 屬於正方 (Pro) 還是反方 (Con)
# target_speech_idx: 代表在對抗中，他所應針對並回應的對手發言在 history 中的 index
# (正一申論 -> 反一質詢正一 -> 反二申論回應正一 -> 正二質詢反二 -> 反一結辯駁斥正一正二 -> 正一結辯全面反擊)
debate_flow = [
    {
        "speaker_role": f"正方一辯 ({st.session_state.pro_1_personality})",
        "action": "申論 (建立己方論點)",
        "short_speaker": "Pro_1",
        "side": "正方",
        "opp_target": None
    },
    {
        "speaker_role": f"反方一辯 ({st.session_state.con_1_personality})",
        "action": "質詢 (針對正方一辯進行單向詰問)",
        "short_speaker": "Con_1",
        "side": "反方",
        "opp_target": 0 # 針對 Pro_1 申論
    },
    {
        "speaker_role": f"反方二辯 ({st.session_state.con_2_personality})",
        "action": "申論 (建立己方論點並回應正方一辯)",
        "short_speaker": "Con_2",
        "side": "反方",
        "opp_target": 0 # 針對 Pro_1 申論進行駁斥
    },
    {
        "speaker_role": f"正方二辯 ({st.session_state.pro_2_personality})",
        "action": "質詢 (針對反方二辯進行單向詰問)",
        "short_speaker": "Pro_2",
        "side": "正方",
        "opp_target": 2 # 針對 Con_2 申論
    },
    {
        "speaker_role": f"反方一辯 ({st.session_state.con_1_personality})",
        "action": "結辯 (總結漏洞並重申立場)",
        "short_speaker": "Con_1",
        "side": "反方",
        "opp_target": None # 全局總結
    },
    {
        "speaker_role": f"正方一辯 ({st.session_state.pro_1_personality})",
        "action": "結辯 (總結漏洞並重申立場)",
        "short_speaker": "Pro_1",
        "side": "正方",
        "opp_target": None # 全局總結
    }
]

# 手動設定面板 (如果沒有勾選自動分配)
if not auto_assign:
    with st.sidebar:
        st.session_state.pro_1_personality = st.selectbox("正方一辯", personalities_list, index=0)
        st.session_state.con_1_personality = st.selectbox("反方一辯", personalities_list, index=1)
        st.session_state.pro_2_personality = st.selectbox("正方二辯", personalities_list, index=3)
        st.session_state.con_2_personality = st.selectbox("反方二辯", personalities_list, index=2)

# ==========================================
# 7. 辯論控制按鈕
# ==========================================
st.subheader("🎮 辯論沙盒控制台")
c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)

with c_btn1:
    if st.button("🚀 開始/重啟辯論", use_container_width=True):
        st.session_state.debate_started = True
        st.session_state.current_step = 0
        st.session_state.debate_history = []
        st.session_state.flow_sheet = "目前為開場階段，雙方尚未交鋒。"
        st.session_state.paused = False
        st.toast("辯論已啟動！")

with c_btn2:
    if st.session_state.debate_started:
        if st.session_state.paused:
            if st.button("▶️ 繼續執行", use_container_width=True):
                st.session_state.paused = False
                st.rerun()
        else:
            if st.button("⏸️ 暫停辯論", use_container_width=True):
                st.session_state.paused = True
                st.toast("已暫停")
                st.rerun()
    else:
        st.button("⏸️ 暫停辯論", disabled=True, use_container_width=True)

with c_btn3:
    if st.session_state.debate_started and not autoplay and st.session_state.current_step < len(debate_flow):
        next_btn = st.button("➡️ 執行單步", use_container_width=True)
    else:
        next_btn = st.button("➡️ 執行單步", disabled=True, use_container_width=True)

with c_btn4:
    if st.button("🔄 重設", use_container_width=True):
        st.session_state.debate_started = False
        st.session_state.current_step = 0
        st.session_state.debate_history = []
        st.session_state.flow_sheet = "目前為開場階段，雙方尚未交鋒。"
        st.session_state.paused = False
        st.rerun()

st.markdown("---")

# ==========================================
# 8. 雙欄佈局：左側辯論歷程，右側爭點摘要與操作
# ==========================================
left_panel, right_panel = st.columns([3, 1])

# 執行辯論的單步 logic
def run_current_step():
    step_info = debate_flow[st.session_state.current_step]
    speaker = step_info["speaker_role"]
    action = step_info["action"]
    side = step_info["side"]
    opp_target_idx = step_info["opp_target"]
    
    # 判斷己方與對手立場
    my_stance = pro_stance if side == "正方" else con_stance
    opp_stance = con_stance if side == "正方" else pro_stance
    
    # 建立目前為止的對話歷程 (Transcript)
    formatted_history = ""
    for idx, msg in enumerate(st.session_state.debate_history):
        formatted_history += f"【步驟 {idx+1}】{msg['speaker']} 進行 {msg['action']}:\n「{msg['content']}」\n\n"
        
    # 如果有特定針對的對手發言 (例如質詢或回應特定申論)
    specific_target_context = ""
    if opp_target_idx is not None and opp_target_idx < len(st.session_state.debate_history):
        target_msg = st.session_state.debate_history[opp_target_idx]
        specific_target_context = f"\n你必須特別針對以下對手的發言進行回應或質詢：\n對手【{target_msg['speaker']}】先前發言：\n「{target_msg['content']}」\n"

    # 進行 API 呼叫
    with st.spinner(f"🤖 {speaker} 正在組織語言與構思論點..."):
        if not api_key:
            speech_text = "[系統警告]: 請先在側邊欄輸入有效的 Google Gemini API 金鑰，否則無法生成內容！"
        else:
            # 提取實際的人格 (括號內的中文)
            match = re.search(r'\((\w+)\)', speaker)
            personality = match.group(1) if match else "理性派"
            
            user_prompt = f"""
            你正在參與一場 2v2 的奧勒岡制辯論比賽。

            辯論議題：【{st.session_state.selected_topic}】
            你的身份：【{speaker}】
            你代表的陣營：【{side}】
            己方陣營的主張立場：『{my_stance}』
            對手陣營的主張立場：『{opp_stance}』

            === 已進行的辯論歷程 (按發言順序) ===
            {formatted_history if formatted_history else "(無，你是開場第一位發言者)"}
            ====================================
            {specific_target_context}

            現在，主席請你進行【{action}】。

            【發言指引】
            1. 請確保你的發言與你的陣營【{side}】立場『{my_stance}』絕對一致，絕對不能倒向對方的立場。
            2. 根據你的任務：
               - 如果你是【申論】：請獨立建立己方的核心論據，或針對已發生的攻防進行立論補強。
               - 如果你是【質詢】：請針對指定對手的發言，挑出邏輯漏洞、論據瑕疵，以犀利且理性的語氣進行單向質問，不需要回答問題。
               - 如果你是【結辯】：請總結整場辯論，駁斥對手陣營的主要論點，並重申己方的論點與立場優勢，完成強力總結。
            3. 注意！不要攻擊你的隊友。請分清誰是隊友（同為{side}），誰是對手（對立陣營）。
            4. 字數請務必控制在 150 字以內，語意要完整且強烈。

            【最終絕對指令】
            請直接用你台詞的第一個字開頭。絕對禁止輸出任何 <think> 標籤、內部推理、草稿、引導語（例如「作為正方...」、「以下是我的發言...」）或前言後語。
            """
            
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=CARDS[personality]
                )
                response = model.generate_content(user_prompt)
                speech_text = clean_output(response.text)
            except Exception as e:
                speech_text = f"[系統呼叫錯誤或超時]: {str(e)}"
    
    # 更新歷史紀錄
    st.session_state.debate_history.append({
        "speaker": speaker,
        "action": action,
        "content": speech_text
    })
    
    # 更新極簡版 Flow Sheet
    if "申論" in action:
        st.session_state.flow_sheet += f"\n- {speaker} 進行了申論，確立核心論點。"
    elif "質詢" in action:
        st.session_state.flow_sheet += f"\n- {speaker} 進行了質詢攻防，質疑對手論證漏洞。"
    elif "結辯" in action:
        st.session_state.flow_sheet += f"\n- {speaker} 進行了結辯，重整戰局與結論。"
        
    st.session_state.current_step += 1

# --- 側邊邏輯觸發器 ---
if st.session_state.debate_started and not st.session_state.paused:
    if st.session_state.current_step < len(debate_flow):
        if autoplay:
            run_current_step()
            # 倒數計時與冷卻
            if st.session_state.current_step < len(debate_flow):
                progress_bar = st.progress(0, text=f"⏳ 系統安全冷卻中，防止 Rate limit API 限制...")
                for i in range(100):
                    time.sleep(cooldown_delay / 100)
                    progress_bar.progress(i + 1, text=f"⏳ 系統安全冷卻中 ({int((100-i-1) * (cooldown_delay/100))}秒剩餘)...")
                progress_bar.empty()
            st.rerun()
        else:
            # 如果不是 autoplay，且被手動點選了「下一步」
            if next_btn:
                run_current_step()
                st.rerun()

# --- 左側面板：辯論歷程舞台 ---
with left_panel:
    st.subheader("🎙️ 辯論直播擂台")
    
    # 進度狀態列
    if st.session_state.debate_started:
        progress_val = st.session_state.current_step / len(debate_flow)
        st.progress(progress_val, text=f"辯論流程進度: 步驟 {st.session_state.current_step} / {len(debate_flow)}")
    else:
        st.info("💡 點選上方「開始/重啟辯論」按鈕，讓 AI 開始精彩交鋒！")
        
    # 渲染對話
    for idx, msg in enumerate(st.session_state.debate_history):
        speaker = msg["speaker"]
        action = msg["action"]
        content = msg["content"]
        
        # 決定頭像圖示與邊框樣式
        avatar = "🤖"
        badge_style = "badge-moderator"
        if "理性派" in speaker:
            avatar = "🔵"
            badge_style = "badge-rational"
        elif "感性派" in speaker:
            avatar = "🔴"
            badge_style = "badge-emotional"
        elif "保守派" in speaker:
            avatar = "🟢"
            badge_style = "badge-conservative"
        elif "改革派" in speaker:
            avatar = "🟣"
            badge_style = "badge-reformist"
        
        # 使用 chat_message 來做氣泡顯示
        with st.chat_message(speaker, avatar=avatar):
            st.markdown(f"<span class='role-badge {badge_style}'>{action}</span>", unsafe_allow_html=True)
            st.write(content)
            
    # 如果正在進行且未結束，顯示下一個發言者的預告
    if st.session_state.debate_started and st.session_state.current_step < len(debate_flow):
        next_step = debate_flow[st.session_state.current_step]
        st.write(f"👨‍⚖️ *主席：接下來將由 **{next_step['speaker_role']}** 進行 **【{next_step['action']}】**...*")
    elif st.session_state.debate_started and st.session_state.current_step >= len(debate_flow):
        st.success("🏆 辯論已順利結束！本場辯論感謝正反雙方精彩對話。")

# --- 右側面板：Flow Sheet、匯出與角色資訊 ---
with right_panel:
    st.subheader("📝 戰局摘要記錄")
    
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("**📌 Flow Sheet (爭點整理)**")
    st.text_area("Debate Summary Log", value=st.session_state.flow_sheet, height=250, disabled=True, label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 匯出報告功能
    if len(st.session_state.debate_history) > 0:
        st.subheader("💾 匯出辯論成果")
        
        # 組裝 Markdown 文字
        md_content = f"# 🏛️ AI 奧勒岡 2v2 辯論紀錄\n\n"
        md_content += f"- **辯論主題**: 【{st.session_state.selected_topic}】\n"
        md_content += f"- **模型設定**: `{model_name}`\n"
        md_content += f"- **角色陣營與立場**:\n"
        md_content += f"  - **正方立場主張**: {pro_stance}\n"
        md_content += f"  - **反方立場主張**: {con_stance}\n"
        md_content += f"  - 正方一辯: {st.session_state.pro_1_personality}\n"
        md_content += f"  - 正方二辯: {st.session_state.pro_2_personality}\n"
        md_content += f"  - 反方一辯: {st.session_state.con_1_personality}\n"
        md_content += f"  - 反方二辯: {st.session_state.con_2_personality}\n\n"
        md_content += "## 🎙️ 辯論發言內容紀錄\n\n"
        
        for msg in st.session_state.debate_history:
            md_content += f"### 🗣️ {msg['speaker']} — 【{msg['action']}】\n"
            md_content += f"{msg['content']}\n\n"
            md_content += "---\n\n"
            
        md_content += "## 📝 戰局摘要紀錄 (Flow Sheet)\n"
        md_content += f"```\n{st.session_state.flow_sheet}\n```\n"
        
        st.download_button(
            label="📥 下載完整辯論紀錄 (.md)",
            data=md_content,
            file_name=f"debate_record_{int(time.time())}.md",
            mime="text/markdown",
            use_container_width=True
        )
    
    # 角色卡快速參考
    st.subheader("ℹ️ 人格特色快速參考")
    with st.expander("📚 點選查看人格描述"):
        st.markdown("**🔵 理性派**")
        st.caption("追求客觀真實、數據證據、邏輯因果，不受情感或政治認同干擾。")
        
        st.markdown("**🔴 感性派**")
        st.caption("重視情感、同理心、個體生命故事、價值體系與弱勢關懷。")
        
        st.markdown("**🟢 保守派**")
        st.caption("重視社會穩定、秩序與法治、歷史傳統累積之智慧、責任倫理，對變革保持謹慎。")
        
        st.markdown("**🟣 改革派**")
        st.caption("勇於挑戰現狀與不公、注重創新與效率、社會公平、適應未來發展趨勢。")
