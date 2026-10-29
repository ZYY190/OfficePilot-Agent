from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)
FONT = Path(r"C:\Windows\Fonts\msyh.ttc")
BOLD = Path(r"C:\Windows\Fonts\msyhbd.ttc")


def font(size, bold=False):
    path = BOLD if bold and BOLD.exists() else FONT
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def center(draw, box, text, size=26, bold=False, fill="#172033"):
    draw.multiline_text(((box[0]+box[2])/2, (box[1]+box[3])/2), text,
                        font=font(size, bold), fill=fill, anchor="mm", align="center", spacing=7)


def arrow(draw, start, end, color="#45688f", width=4):
    draw.line([start, end], fill=color, width=width)
    x1,y1=start; x2,y2=end
    if abs(x2-x1) >= abs(y2-y1):
        d = 1 if x2>x1 else -1
        points=[(x2,y2),(x2-d*16,y2-8),(x2-d*16,y2+8)]
    else:
        d = 1 if y2>y1 else -1
        points=[(x2,y2),(x2-8,y2-d*16),(x2+8,y2-d*16)]
    draw.polygon(points, fill=color)


def box(draw, box, text, fill="#e8f0ff", outline="#3f68b5", size=24, bold=False):
    draw.rounded_rectangle(box, radius=18, fill=fill, outline=outline, width=3)
    center(draw, box, text, size=size, bold=bold)


def architecture():
    image=Image.new("RGB",(1800,1050),"white")
    draw=ImageDraw.Draw(image)
    center(draw,(0,35,1800,90),"OfficePilot 智能体总体架构",size=42,bold=True)
    box(draw,(70,170,390,290),"用户\n自然语言输入")
    box(draw,(500,170,900,290),"Web 前端\n聊天界面 / 工具轨迹")
    box(draw,(1010,170,1390,290),"Agent Runtime\n会话状态与任务编排")
    box(draw,(1490,170,1730,290),"SQLite\n多轮记忆")
    box(draw,(1010,420,1390,560),"Planner\n可选 LLM 工具选择\n离线规则回退",fill="#fff3d6",outline="#c68416")
    box(draw,(500,700,900,850),"MCP Client\nJSON-RPC over stdio")
    box(draw,(1010,700,1390,850),"MCP Server\ninitialize / tools/list / tools/call")
    box(draw,(80,700,400,850),"办公工具\n待办 / 计算 / 文件",fill="#e9f9ef",outline="#31935b")
    box(draw,(1490,700,1730,850),"外部 API\nwttr.in 天气",fill="#f3e8ff",outline="#7b4bb7")
    arrow(draw,(390,230),(500,230))
    arrow(draw,(900,230),(1010,230))
    arrow(draw,(1390,210),(1490,210))
    arrow(draw,(1200,290),(1200,420))
    arrow(draw,(1010,490),(900,700))
    arrow(draw,(900,775),(1010,775))
    arrow(draw,(1010,800),(400,800))
    arrow(draw,(1390,780),(1490,780))
    arrow(draw,(1200,560),(1200,700))
    image.save(OUT/"architecture.png")
    image.close()


def flow():
    image=Image.new("RGB",(1500,1550),"white")
    draw=ImageDraw.Draw(image)
    center(draw,(0,35,1500,90),"一次对话的业务流程",size=42,bold=True)
    items=[
        ("用户输入自然语言", "#e8f0ff"),
        ("读取历史消息与当前会话状态", "#eef7ff"),
        ("Planner 判断意图并选择工具", "#fff3d6"),
        ("MCP Client 发起 tools/call", "#e8f0ff"),
        ("MCP Server 执行工具", "#e8f0ff"),
        ("SQLite / 工作区 / 外部 API", "#e9f9ef"),
        ("更新会话记忆与最近任务", "#f3e8ff"),
        ("生成自然语言回复并返回前端", "#e8f0ff"),
    ]
    y=150
    boxes=[]
    for text,fill in items:
        rect=(330,y,1170,y+110)
        box(draw,rect,text,fill=fill,size=27)
        boxes.append(rect)
        y+=165
    for a,b in zip(boxes,boxes[1:]):
        arrow(draw,((a[0]+a[2])//2,a[3]),( (b[0]+b[2])//2,b[1]))
    image.save(OUT/"business-flow.png")
    image.close()

architecture()
flow()
print("DIAGRAMS_CREATED", OUT)
