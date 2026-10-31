import streamlit as st
from datetime import datetime
import shlex
import json
import html

st.set_page_config(page_title="MiniOS Web Simulator", page_icon="💻", layout="wide", initial_sidebar_state="collapsed")

TOTAL_RAM_MB = 256

def create_directory():
    return {"type": "directory", "children": {}}

def create_file(content=""):
    return {"type": "file", "content": content}

def create_initial_filesystem():
    fs = create_directory()
    fs["children"]["documents"] = create_directory()
    fs["children"]["home"] = create_directory()
    fs["children"]["system"] = create_directory()
    fs["children"]["home"]["children"]["Ashish"] = create_directory()
    fs["children"]["home"]["children"]["Ashish"]["children"]["project"] = create_directory()
    fs["children"]["home"]["children"]["Ashish"]["children"]["project"]["children"]["demo.txt"] = create_file("MiniOS Demo File")
    fs["children"]["home"]["children"]["Ashish"]["children"]["welcome.txt"] = create_file("Welcome to MiniOS GUI!")
    return fs

def get_node(path):
    node = st.session_state.fs
    for part in path:
        if node["type"] != "directory":
            return None
        node = node["children"].get(part)
        if node is None:
            return None
    return node

def resolve_path(path):
    parts = [] if path.startswith("/") else st.session_state.cwd.copy()
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
        else:
            parts.append(part)
    return parts

def fmt_path(path):
    return "/" + "/".join(path) if path else "/"

def init_state():
    if "fs" not in st.session_state:
        st.session_state.fs = create_initial_filesystem()
    if "cwd" not in st.session_state:
        st.session_state.cwd = ["home", "Ashish"]
    if get_node(st.session_state.cwd) is None:
        st.session_state.cwd = []
    if "processes" not in st.session_state:
        st.session_state.processes = [
            {"pid": 1, "name": "init", "status": "Running", "memory": 12, "burst_time": 3},
            {"pid": 2, "name": "minios-shell", "status": "Running", "memory": 20, "burst_time": 5},
            {"pid": 3, "name": "file-manager", "status": "Sleeping", "memory": 16, "burst_time": 2},
        ]
    if "next_pid" not in st.session_state:
        st.session_state.next_pid = 4
    if "blocks" not in st.session_state:
        st.session_state.blocks = []
    if "next_block_id" not in st.session_state:
        st.session_state.next_block_id = 1
    if "history" not in st.session_state:
        st.session_state.history = [
            "Welcome to MiniOS GUI Simulator!",
            "Type 'help' to see available the all commands in linux os for doubt clearning of linux program."
        ]

def add(message=""):
    st.session_state.history.append(str(message))

def command(raw):
    raw = raw.strip()
    if not raw:
        return
    add(f"{fmt_path(st.session_state.cwd)} $ {raw}")
    try:
        args = shlex.split(raw)
    except ValueError as e:
        add(f"Syntax error: {e}")
        return
    cmd, params = args[0].lower(), args[1:]
    node = get_node(st.session_state.cwd)

    if cmd == "help":
        add("""Available Commands:
help | ls | pwd | cd PATH | mkdir NAME | touch NAME
write FILE TEXT | cat FILE | rm FILE | rmdir NAME | tree
ps | run NAME | kill PID | top
mem | memalloc SIZE_MB | memfree BLOCK_ID
schedule fcfs | schedule rr [QUANTUM] | date | clear | reset""")
    elif cmd == "pwd":
        add(fmt_path(st.session_state.cwd))
    elif cmd == "ls":
        if not node["children"]:
            add("(Empty directory)")
        for name, item in sorted(node["children"].items()):
            add(f"[DIR]  {name}/" if item["type"] == "directory" else f"[FILE] {name}")
    elif cmd == "cd":
        if len(params) != 1:
            add("Usage: cd path")
        else:
            target_path = resolve_path(params[0])
            target = get_node(target_path)
            if target is None:
                add("Error: Path not found.")
            elif target["type"] != "directory":
                add("Error: Not a directory.")
            else:
                st.session_state.cwd = target_path
    elif cmd in ("mkdir", "touch"):
        if len(params) != 1 or "/" in params[0] or params[0] in (".", ".."):
            add(f"Usage: {cmd} name")
        elif params[0] in node["children"]:
            add("Error: Name already exists.")
        else:
            node["children"][params[0]] = create_directory() if cmd == "mkdir" else create_file()
            add(f"{'Directory' if cmd == 'mkdir' else 'File'} '{params[0]}' created.")
    elif cmd == "write":
        if len(params) < 2:
            add("Usage: write file_name text")
        else:
            item = node["children"].get(params[0])
            if item is None:
                add("Error: File not found.")
            elif item["type"] != "file":
                add("Error: This is a directory.")
            else:
                item["content"] = " ".join(params[1:])
                add(f"Content saved to '{params[0]}'.")
    elif cmd == "cat":
        if len(params) != 1:
            add("Usage: cat file_name")
        else:
            item = node["children"].get(params[0])
            if item is None:
                add("Error: File not found.")
            elif item["type"] != "file":
                add("Error: Cannot read a directory.")
            else:
                add(item["content"] or "(Empty file)")
    elif cmd in ("rm", "rmdir"):
        if len(params) != 1:
            add(f"Usage: {cmd} name")
        else:
            item = node["children"].get(params[0])
            expected = "file" if cmd == "rm" else "directory"
            if item is None:
                add("Error: Item not found.")
            elif item["type"] != expected:
                add("Error: Wrong item type for this command.")
            elif expected == "directory" and item["children"]:
                add("Error: Directory is not empty.")
            else:
                del node["children"][params[0]]
                add(f"{'File' if expected == 'file' else 'Directory'} '{params[0]}' deleted.")
    elif cmd == "tree":
        add("Virtual file system tree is shown in the left panel.")
    elif cmd == "ps":
        add("PID   STATUS     MEMORY   PROCESS")
        for p in st.session_state.processes:
            add(f"{p['pid']:<5} {p['status']:<10} {p['memory']:<8} MB {p['name']}")
    elif cmd == "run":
        if not params:
            add("Usage: run process_name")
        else:
            name = " ".join(params)
            if any(p["name"].lower() == name.lower() for p in st.session_state.processes):
                add(f"Error: Process '{name}' is already listed.")
            else:
                pid = st.session_state.next_pid
                st.session_state.processes.append({
                    "pid": pid, "name": name, "status": "Running",
                    "memory": 8 + len(name) * 2, "burst_time": 2 + len(name) % 5
                })
                st.session_state.next_pid += 1
                add(f"Process '{name}' started with PID {pid}.")
    elif cmd == "kill":
        if len(params) != 1 or not params[0].isdigit():
            add("Usage: kill PID")
        else:
            pid = int(params[0])
            p = next((p for p in st.session_state.processes if p["pid"] == pid), None)
            if p is None:
                add(f"Error: No process found with PID {pid}.")
            elif p["name"] in ("init", "minios-shell"):
                add(f"Error: Core process '{p['name']}' cannot be stopped.")
            else:
                st.session_state.processes.remove(p)
                add(f"Process '{p['name']}' (PID {pid}) stopped.")
    elif cmd == "top":
        used = sum(b["size"] for b in st.session_state.blocks)
        add(f"MiniOS Process Monitor — {datetime.now().strftime('%H:%M:%S')}")
        add(f"Processes: {len(st.session_state.processes)}")
        add(f"Process memory estimate: {sum(p['memory'] for p in st.session_state.processes)} MB")
        add(f"Memory-manager allocations: {used}/{TOTAL_RAM_MB} MB")
    elif cmd == "mem":
        used = sum(b["size"] for b in st.session_state.blocks)
        add("MiniOS Memory Manager (SIMULATED RAM)")
        add(f"Total RAM: {TOTAL_RAM_MB} MB | Used: {used} MB | Free: {TOTAL_RAM_MB-used} MB")
        if st.session_state.blocks:
            for b in st.session_state.blocks:
                add(f"ID {b['id']}: {b['size']} MB — {b['owner']}")
        else:
            add("No memory blocks allocated yet.")
    elif cmd == "memalloc":
        if len(params) != 1 or not params[0].isdigit() or int(params[0]) <= 0:
            add("Usage: memalloc SIZE_MB (positive whole number)")
        else:
            size = int(params[0])
            used = sum(b["size"] for b in st.session_state.blocks)
            if size > TOTAL_RAM_MB - used:
                add(f"Error: Not enough simulated RAM. Available: {TOTAL_RAM_MB-used} MB.")
            else:
                bid = st.session_state.next_block_id
                st.session_state.blocks.append({"id": bid, "size": size, "owner": "user allocation"})
                st.session_state.next_block_id += 1
                add(f"Allocated {size} MB simulated RAM in block {bid}.")
    elif cmd == "memfree":
        if len(params) != 1 or not params[0].isdigit():
            add("Usage: memfree BLOCK_ID")
        else:
            bid = int(params[0])
            b = next((b for b in st.session_state.blocks if b["id"] == bid), None)
            if b is None:
                add(f"Error: No allocated memory block with ID {bid}.")
            else:
                st.session_state.blocks.remove(b)
                add(f"Freed {b['size']} MB from memory block {bid}.")
    elif cmd == "schedule":
        if not params or params[0].lower() not in ("fcfs", "rr") or len(params) > 2:
            add("Usage: schedule fcfs OR schedule rr [time_quantum]")
            return
        algo = params[0].lower()
        quantum = 2
        if algo == "rr" and len(params) == 2:
            if not params[1].isdigit() or int(params[1]) <= 0:
                add("Error: Round Robin time quantum must be a positive whole number.")
                return
            quantum = int(params[1])
        jobs = [{"pid": p["pid"], "name": p["name"], "burst": max(1, int(p.get("burst_time", 3)))}
                for p in st.session_state.processes]
        add(f"CPU Scheduling Simulation: {algo.upper()}")
        if algo == "fcfs":
            clock = wait_total = turn_total = 0
            for j in jobs:
                finish = clock + j["burst"]
                add(f"{clock} -> {finish}: PID {j['pid']} ({j['name']}) | waiting={clock}, turnaround={finish}")
                wait_total += clock
                turn_total += finish
                clock = finish
        else:
            remaining = {j["pid"]: j["burst"] for j in jobs}
            completion, clock = {}, 0
            while any(v > 0 for v in remaining.values()):
                for j in jobs:
                    pid = j["pid"]
                    if remaining[pid] <= 0:
                        continue
                    run_for = min(quantum, remaining[pid])
                    start = clock
                    clock += run_for
                    remaining[pid] -= run_for
                    add(f"{start} -> {clock}: PID {pid} ({j['name']})")
                    if remaining[pid] == 0:
                        completion[pid] = clock
            wait_total = turn_total = 0
            for j in jobs:
                turn = completion[j["pid"]]
                wait = turn - j["burst"]
                add(f"PID {j['pid']} ({j['name']}): waiting={wait}, turnaround={turn}")
                wait_total += wait
                turn_total += turn
        if jobs:
            add(f"Average waiting time: {wait_total/len(jobs):.2f} units")
            add(f"Average turnaround time: {turn_total/len(jobs):.2f} units")
    elif cmd == "date":
        add(datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
    elif cmd == "clear":
        st.session_state.history = []
    elif cmd == "reset":
        st.session_state.fs = create_initial_filesystem()
        st.session_state.cwd = ["home", "Ashish"]
        st.session_state.processes = [
            {"pid": 1, "name": "init", "status": "Running", "memory": 12, "burst_time": 3},
            {"pid": 2, "name": "minios-shell", "status": "Running", "memory": 20, "burst_time": 5},
            {"pid": 3, "name": "file-manager", "status": "Sleeping", "memory": 16, "burst_time": 2},
        ]
        st.session_state.next_pid = 4
        st.session_state.blocks = []
        st.session_state.next_block_id = 1
        st.session_state.history = [
            "Welcome to MiniOS GUI Simulator!",
            "Type 'help' to see available the all commands in linux os for doubt clearning of linux program."
        ]
    else:
        add(f"Unknown command: {cmd}")
        add("Type 'help' to see available commands.")

def render_tree_lines(node, depth=1):
    lines = []
    indent = "&nbsp;" * (depth * 4)
    for name, item in sorted(node["children"].items()):
        safe_name = html.escape(name)
        if item["type"] == "directory":
            arrow = "▾ " if item["children"] else "&nbsp;&nbsp;"
            lines.append(f'<div class="tree-item">{indent}{arrow}{safe_name}/</div>')
            lines.extend(render_tree_lines(item, depth + 1))
        else:
            lines.append(f'<div class="tree-item file-item">{indent}&nbsp;&nbsp;{safe_name}</div>')
    return lines

init_state()

# Custom CSS to match the exact Tkinter GUI look
st.markdown("""
<style>
/* Hide default Streamlit elements */
header[data-testid="stHeader"] {display: none !important;}
section[data-testid="stSidebar"] {display: none !important;}
#MainMenu, footer {visibility: hidden;}

/* App background and spacing */
.stApp {
    background-color: #0b131e !important;
    color: #ffffff !important;
}
.block-container {
    padding-top: 0.6rem !important;
    padding-bottom: 0.5rem !important;
    padding-left: 1.2rem !important;
    padding-right: 1.2rem !important;
    max-width: 100% !important;
}

/* Header & Status Bar */
.minios-topbar {
    background-color: #101c2b;
    padding: 12px 20px;
    display: flex;
    align-items: baseline;
    gap: 16px;
    border-bottom: 1px solid #1c2d42;
}
.minios-logo {
    color: #2ecc71;
    font-size: 26px;
    font-weight: 800;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    letter-spacing: 1px;
}
.minios-subtitle {
    color: #c8d6e5;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.8px;
}
.minios-statusbar {
    background-color: #162638;
    padding: 6px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    border-bottom: 1px solid #223852;
    font-family: 'Segoe UI', sans-serif;
}
.status-left {
    color: #2ecc71;
    font-size: 12px;
    font-weight: 700;
}
.status-right {
    color: #dbe4ee;
    font-size: 12px;
    font-weight: 700;
}

/* Panel Headers */
.panel-title {
    color: #2ecc71;
    font-size: 13px;
    font-weight: 800;
    margin-bottom: 6px;
    letter-spacing: 0.6px;
    font-family: 'Segoe UI', sans-serif;
}

/* Left Virtual File System Box */
.vfs-container {
    background-color: #1a2a3a;
    border: 2px solid #b8c6d4;
    height: 430px;
    padding: 10px 12px;
    overflow-y: auto;
    font-family: 'Segoe UI', Tahoma, sans-serif;
    font-size: 13.5px;
    color: #ffffff;
}
.tree-item {
    line-height: 1.65;
    white-space: nowrap;
    font-weight: 600;
}
.file-item {
    color: #e2eef8;
    font-weight: 500;
}

/* Right Terminal Box */
.terminal-container {
    background-color: #060a0f;
    border: 1px solid #1c2d42;
    height: 430px;
    padding: 14px 16px;
    overflow-y: auto;
    white-space: pre-wrap;
    font-family: Consolas, 'Courier New', monospace;
    font-size: 14px;
    color: #2ecc71;
    line-height: 1.45;
}

/* Command Bar Styling */
div[data-testid="stForm"] {
    background-color: #101c2b !important;
    border: 1px solid #1e3046 !important;
    border-radius: 3px !important;
    padding: 6px 12px !important;
    margin-top: 8px !important;
}
.cmd-badge {
    background-color: #2ecc71;
    color: #060a0f;
    font-weight: 800;
    font-size: 12px;
    padding: 8px 10px;
    border-radius: 2px;
    display: inline-block;
    margin-top: 3px;
    font-family: Consolas, monospace;
}

/* Force Dark Input Box */
div[data-baseweb="input"] {
    background-color: #060a0f !important;
    border: 1px solid #1f3349 !important;
    border-radius: 2px !important;
}
div[data-baseweb="input"] input {
    color: #2ecc71 !important;
    -webkit-text-fill-color: #2ecc71 !important;
    font-family: Consolas, monospace !important;
    font-size: 14px !important;
    caret-color: #2ecc71 !important;
}

/* Green RUN Button */
div[data-testid="stFormSubmitButton"] > button {
    background-color: #2ecc71 !important;
    color: #050a0f !important;
    border: none !important;
    border-radius: 2px !important;
    font-weight: 800 !important;
    height: 38px !important;
}
div[data-testid="stFormSubmitButton"] > button:hover {
    background-color: #27ae60 !important;
    color: #000000 !important;
}

/* Bottom Clear / Action Buttons */
div.stButton > button, div.stDownloadButton > button {
    background-color: #1d3044 !important;
    color: #d8e4f0 !important;
    border: 1px solid #2b4460 !important;
    border-radius: 2px !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    padding: 4px 14px !important;
    height: 32px !important;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
    background-color: #274059 !important;
    color: #ffffff !important;
}
.footer-label {
    text-align: right;
    color: #8fa4b8;
    font-size: 12px;
    font-weight: 600;
    padding-top: 6px;
    font-family: 'Segoe UI', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# 1. Top Title Bar & Status Bar
current_path_str = fmt_path(st.session_state.cwd)
st.markdown(f"""
<div class="minios-topbar">
    <span class="minios-logo">MINIOS</span>
    <span class="minios-subtitle">VIRTUAL OPERATING SYSTEM SIMULATOR</span>
</div>
<div class="minios-statusbar">
    <span class="status-left">● SYSTEM RUNNING</span>
    <span class="status-right">PATH: {html.escape(current_path_str)}</span>
</div>
""", unsafe_allow_html=True)

# 2. Main Split Layout (Left: Virtual File System | Right: Terminal)
left_col, right_col = st.columns([1, 2.7], gap="medium")

with left_col:
    tree_html = '<div class="tree-item">▾ /</div>' + "".join(render_tree_lines(st.session_state.fs, 1))
    st.markdown(f"""
    <div class="panel-title">VIRTUAL FILE SYSTEM</div>
    <div class="vfs-container">{tree_html}</div>
    """, unsafe_allow_html=True)

with right_col:
    term_text = "\n".join(st.session_state.history[-100:])
    safe_term = html.escape(term_text)
    st.markdown(f"""
    <div class="panel-title">TERMINAL</div>
    <div class="terminal-container" id="term-box">
        {safe_term}
        <div id="bottom-anchor"></div>
    </div>
    <script>
        setTimeout(function() {{
            var anchor = document.getElementById("bottom-anchor");
            if (anchor) {{
                anchor.scrollIntoView({{ behavior: "smooth", block: "end" }});
            }}
        }}, 150);
    </script>
    """, unsafe_allow_html=True)

# 3. Bottom Command Input Bar
with st.form("command_form", clear_on_submit=True):
    c1, c2, c3 = st.columns([0.9, 8.1, 0.8], gap="small")
    with c1:
        st.markdown('<div class="cmd-badge">COMMAND &gt;</div>', unsafe_allow_html=True)
    with c2:
        entered = st.text_input("COMMAND", label_visibility="collapsed", placeholder="Type command here (e.g., help, ls, ps, top, mem)...")
    with c3:
        submitted = st.form_submit_button("RUN", use_container_width=True)

if submitted and entered:
    command(entered)
    st.rerun()

# 4. Footer Row (CLEAR TERMINAL & Simulator Tag)
f1, f2, f3, f4 = st.columns([1.3, 1.2, 1.5, 6.0], gap="small")
with f1:
    if st.button("CLEAR TERMINAL", use_container_width=True):
        command("clear")
        st.rerun()
with f2:
    if st.button("RESET MINIOS", use_container_width=True):
        command("reset")
        st.rerun()
with f3:
    st.download_button(
        "EXPORT JSON",
        data=json.dumps(st.session_state.fs, indent=4, ensure_ascii=False),
        file_name="minios_data.json",
        mime="application/json",
        use_container_width=True
    )
with f4:
    st.markdown('<div class="footer-label">MiniOS Educational Simulator | Python + Tkinter</div>', unsafe_allow_html=True)
