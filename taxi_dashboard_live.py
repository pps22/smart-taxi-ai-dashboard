import time
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

from taxiagent_perfect import GridWorld, Passenger, Performance, TaxiAgent

Position = Tuple[int, int]

st.set_page_config(
    page_title="Live Smart Taxi Dashboard",
    page_icon="🚕",
    layout="wide",
    initial_sidebar_state="expanded",
)

SCENARIOS: Dict[str, Dict] = {
    "Standard Pickup and Delivery": {
        "size": 5,
        "start": (0, 0),
        "blocked": {(2, 2), (3, 1)},
        "traffic_costs": {(1, 1): 2, (1, 2): 1, (2, 1): 2},
        "pickup": (1, 2),
        "destination": (4, 4),
        "name": "Scenario 1 - Standard Pickup and Delivery",
        "fare": 250,
    },
    "Traffic-Aware Route Choice": {
        "size": 6,
        "start": (0, 0),
        "blocked": {(1, 1), (1, 2), (2, 2), (4, 3)},
        "traffic_costs": {(2, 0): 3, (3, 0): 2, (4, 0): 1},
        "pickup": (3, 0),
        "destination": (5, 4),
        "name": "Scenario 2 - Traffic-Aware Route Choice",
        "fare": 280,
    },
    "Long Detour Around Blocked Corridor": {
        "size": 6,
        "start": (5, 0),
        "blocked": {(1, 3), (2, 3), (3, 3), (4, 3), (3, 1)},
        "traffic_costs": {(5, 1): 2, (4, 1): 2, (2, 2): 3, (0, 4): 2},
        "pickup": (2, 4),
        "destination": (0, 5),
        "name": "Scenario 3 - Long Detour Around Blocked Corridor",
        "fare": 265,
    },
}

THEME = """
<style>
.block-container {padding-top: 1.1rem; padding-bottom: 1rem;}
.hero {
    background: linear-gradient(120deg, #0f172a 0%, #1d4ed8 55%, #10b981 100%);
    color: white; padding: 1.2rem 1.3rem; border-radius: 22px; margin-bottom: 1rem;
    box-shadow: 0 14px 30px rgba(15, 23, 42, 0.20);
}
.hero h1 {margin: 0; font-size: 2rem;}
.hero p {margin: 0.35rem 0 0 0; opacity: .93;}
.card {
    background: white; border-radius: 18px; padding: 1rem 1rem .8rem 1rem;
    border: 1px solid rgba(15,23,42,.08); box-shadow: 0 10px 24px rgba(15,23,42,.06);
}
.metric-card {
    background: linear-gradient(135deg, #111827 0%, #1f2937 100%); color: white;
    padding: 1rem 1.1rem; border-radius: 18px; min-height: 110px;
    border: 1px solid rgba(255,255,255,.08); box-shadow: 0 10px 24px rgba(0,0,0,.18);
}
.metric-label {font-size: .9rem; opacity: .82; margin-bottom: .35rem;}
.metric-value {font-size: 2rem; font-weight: 700; line-height: 1.08;}
.metric-sub {font-size: .86rem; opacity: .78; margin-top: .35rem;}
.status-pill {display:inline-block; padding:.3rem .7rem; border-radius:999px; font-weight:700; font-size:.85rem;}
.status-running {background:#dcfce7; color:#166534;}
.status-paused {background:#fef3c7; color:#92400e;}
.status-complete {background:#dbeafe; color:#1d4ed8;}
.status-error {background:#fee2e2; color:#991b1b;}
.log-box {
    background:#0b1220; color:#e5e7eb; padding:1rem; border-radius:16px; min-height: 180px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size:.9rem;
}
.small-note {color:#475569; font-size:.93rem;}
</style>
"""


def metric_card(label: str, value: str, sub: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_env(config: Dict) -> GridWorld:
    return GridWorld(
        size=config["size"],
        start=config["start"],
        blocked=set(config["blocked"]),
        traffic_costs=dict(config["traffic_costs"]),
        passenger=Passenger(config["pickup"], config["destination"]),
        name=config["name"],
    )


def create_simulation(config: Dict) -> Dict:
    env = build_env(config)
    agent = TaxiAgent(env)
    perf = Performance()
    return {
        "scenario_key": None,
        "agent": agent,
        "perf": perf,
        "trace": [env.start],
        "events": [f"Simulation initialized at {env.start}. Target pickup is {env.passenger.pickup}."],
        "status": "ready",
        "last_reason": "Simulation ready.",
        "last_action": None,
        "current_goal": env.passenger.pickup,
        "completed": False,
        "failed": False,
        "tick": 0,
    }


def ensure_state(selected_key: str) -> Dict:
    config = SCENARIOS[selected_key]
    if "sim" not in st.session_state:
        st.session_state.sim = create_simulation(config)
        st.session_state.sim["scenario_key"] = selected_key
        st.session_state.autoplay = False
        st.session_state.speed = 0.7
    elif st.session_state.sim.get("scenario_key") != selected_key:
        st.session_state.sim = create_simulation(config)
        st.session_state.sim["scenario_key"] = selected_key
        st.session_state.autoplay = False
    return st.session_state.sim


def simulation_status(sim: Dict) -> str:
    if sim["completed"]:
        return "Trip completed"
    if sim["failed"]:
        return "Route failed"
    if sim["status"] == "running":
        return "Running"
    if sim["status"] == "paused":
        return "Paused"
    return "Ready"


def status_class(text: str) -> str:
    if text == "Trip completed":
        return "status-complete"
    if text == "Route failed":
        return "status-error"
    if text == "Running":
        return "status-running"
    return "status-paused"


def perform_step(sim: Dict) -> None:
    if sim["completed"] or sim["failed"]:
        sim["status"] = "paused"
        return

    agent: TaxiAgent = sim["agent"]
    perf: Performance = sim["perf"]
    sim["tick"] += 1
    sim["status"] = "running"

    # Pickup event
    if not agent.has_passenger and agent.location == agent.env.passenger.pickup and not agent.env.passenger.picked_up:
        agent.try_pickup(perf)
        sim["current_goal"] = agent.env.passenger.destination
        sim["last_action"] = "Pick up passenger"
        sim["last_reason"] = agent.explanations[-1]
        sim["events"].append(f"Step {perf.steps}: Passenger picked up at {agent.location}.")
        return

    # Dropoff event
    if agent.location == agent.env.passenger.destination and agent.has_passenger:
        agent.try_dropoff(perf)
        sim["completed"] = True
        sim["status"] = "completed"
        sim["current_goal"] = agent.location
        sim["last_action"] = "Drop off passenger"
        sim["last_reason"] = agent.explanations[-1]
        sim["events"].append(
            f"Step {perf.steps}: Passenger dropped off at {agent.location}. Final score {perf.score}."
        )
        return

    target = agent.mission_target()
    sim["current_goal"] = target
    action = agent.choose_next_action(target)
    if action is None:
        perf.register_replan("No safe path exists.")
        sim["failed"] = True
        sim["status"] = "failed"
        sim["last_action"] = "No action"
        sim["last_reason"] = agent.explanations[-1] if agent.explanations else "No valid route found."
        sim["events"].append(f"Simulation failed at {agent.location}. No route to {target}.")
        return

    nxt = agent.preview_move(action)
    applied = agent.apply_action(action, perf)
    sim["last_action"] = action
    sim["last_reason"] = agent.explanations[-1]

    if applied:
        sim["trace"].append(agent.location)
        sim["events"].append(
            f"Step {perf.steps}: Taxi moved {action} to {agent.location} (cell cost {agent.env.cell_cost(agent.location)})."
        )
    else:
        sim["events"].append(f"Invalid move attempt toward {nxt}.")


def reset_simulation(selected_key: str) -> None:
    st.session_state.sim = create_simulation(SCENARIOS[selected_key])
    st.session_state.sim["scenario_key"] = selected_key
    st.session_state.autoplay = False


def route_lookup(trace: List[Position]) -> Dict[Position, int]:
    first_seen: Dict[Position, int] = {}
    for idx, pos in enumerate(trace):
        if pos not in first_seen:
            first_seen[pos] = idx
    return first_seen


def render_grid(sim: Dict, config: Dict) -> str:
    size = config["size"]
    blocked = set(config["blocked"])
    traffic = dict(config["traffic_costs"])
    start = config["start"]
    pickup = config["pickup"]
    destination = config["destination"]
    trace = sim["trace"]
    current = sim["agent"].location
    passenger = sim["agent"].env.passenger
    steps = route_lookup(trace)

    cells = []
    for r in range(size):
        for c in range(size):
            pos = (r, c)
            classes = ["cell"]
            badge = ""
            subtitle = ""
            if pos in blocked:
                classes.append("blocked")
                badge = "⛔"
                subtitle = "Blocked"
            else:
                if pos == start:
                    classes.append("start")
                    subtitle = "Start"
                if pos == pickup and not passenger.picked_up:
                    classes.append("pickup")
                    badge = "🧍"
                    subtitle = "Waiting"
                if pos == destination:
                    classes.append("dropoff")
                    if not badge:
                        badge = "🏁"
                    subtitle = "Destination"
                if pos in traffic:
                    classes.append("traffic")
                    if subtitle in {"", "Start"}:
                        subtitle = f"Traffic +{traffic[pos]}"
                if pos in steps:
                    classes.append("visited")
                if pos == current:
                    classes.append("current")
                    badge = "🚕"
                    subtitle = "Taxi"
                if passenger.picked_up and not passenger.delivered and pos == current:
                    subtitle = "Taxi + passenger"
                if passenger.delivered and pos == destination:
                    badge = "✅"
                    subtitle = "Delivered"

            step_html = f'<div class="step">{steps[pos]}</div>' if pos in steps else ""
            traffic_html = f'<div class="mini">+{traffic[pos]}</div>' if pos in traffic and pos not in blocked else ""
            cells.append(
                f'<div class="{" ".join(classes)}"><div class="coord">{r},{c}</div>{step_html}<div class="emoji">{badge}</div>{traffic_html}<div class="subtitle">{subtitle}</div></div>'
            )

    return f"""
    <style>
    .grid-wrap {{display:grid; grid-template-columns: repeat({size}, minmax(84px, 1fr)); gap:10px; margin-top: .8rem;}}
    .cell {{position:relative; min-height:92px; border-radius:18px; padding:8px; background:#f8fafc; border:1px solid #dbeafe; overflow:hidden;}}
    .cell.visited {{box-shadow: inset 0 0 0 2px #93c5fd;}}
    .cell.current {{background:#dbeafe; border:2px solid #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.12);}}
    .cell.start {{background:#eff6ff;}}
    .cell.pickup {{background:#dcfce7; border-color:#facc15;}}
    .cell.dropoff {{background:#f5f3ff; border-color:#c4b5fd;}}
    .cell.blocked {{background:#0f172a; color:white; border-color:#111827;}}
    .cell.traffic:not(.blocked) {{border-color:#f59e0b;}}
    .coord {{font-size:.8rem; color:#64748b;}}
    .blocked .coord {{color:#cbd5e1;}}
    .emoji {{font-size:1.3rem; margin-top:.3rem;}}
    .subtitle {{position:absolute; left:8px; bottom:8px; font-size:.82rem; color:#334155;}}
    .blocked .subtitle {{color:#e2e8f0;}}
    .step {{position:absolute; top:8px; right:8px; width:28px; height:28px; border-radius:999px; background:#0f172a; color:white; display:flex; align-items:center; justify-content:center; font-size:.8rem; font-weight:700;}}
    .mini {{position:absolute; left:8px; top:26px; font-size:.75rem; font-weight:700; color:#92400e;}}
    </style>
    <div class="grid-wrap">{''.join(cells)}</div>
    """


def make_kpis(sim: Dict, config: Dict) -> Dict[str, float]:
    perf: Performance = sim["perf"]
    fare = config["fare"] if perf.goal_achieved else 0
    operating_cost = 30 + perf.path_cost * 2 + perf.invalid_attempts * 12 + perf.replans * 6
    profit = fare - operating_cost
    progress = 100 if sim["completed"] else min(95, max(10, len(sim["trace"]) * 100 / (config["size"] * 2)))
    trust = min(100, 70 + len(sim["agent"].explanations) * 3)
    return {
        "fare": fare,
        "operating_cost": operating_cost,
        "profit": profit,
        "progress": progress,
        "trust": trust,
        "success_rate": 100 if perf.goal_achieved else 0,
    }


def event_table(sim: Dict) -> pd.DataFrame:
    rows = []
    for idx, text in enumerate(sim["events"], start=1):
        rows.append({"#": idx, "Event": text})
    return pd.DataFrame(rows)


st.markdown(THEME, unsafe_allow_html=True)
st.markdown(
    """
    <div class="hero">
        <h1>🚕 Live Smart Taxi Dashboard</h1>
        <p>Watch the taxi move step by step, pick up the passenger, deliver them, and update score, cost, and business metrics automatically.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Control Panel")
    selected_key = st.selectbox("Choose scenario", list(SCENARIOS.keys()))
    sim = ensure_state(selected_key)
    config = SCENARIOS[selected_key]

    st.subheader("Simulation Controls")
    speed = st.slider("Auto-play speed (seconds per step)", 0.2, 2.0, st.session_state.get("speed", 0.7), 0.1)
    st.session_state.speed = speed

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("▶ Start / Resume", use_container_width=True):
            st.session_state.autoplay = True
            sim["status"] = "running"
    with col_b:
        if st.button("⏸ Pause", use_container_width=True):
            st.session_state.autoplay = False
            if not sim["completed"] and not sim["failed"]:
                sim["status"] = "paused"

    col_c, col_d = st.columns(2)
    with col_c:
        if st.button("⏭ Next step", use_container_width=True):
            st.session_state.autoplay = False
            perform_step(sim)
    with col_d:
        if st.button("🔄 Reset", use_container_width=True):
            reset_simulation(selected_key)
            sim = st.session_state.sim

    st.caption("This version updates route, score, cost, and passenger status while the trip is running.")
    st.divider()
    st.subheader("Scenario Setup")
    st.write(f"**Grid size:** {config['size']} × {config['size']}")
    st.write(f"**Start:** {config['start']}")
    st.write(f"**Pickup:** {config['pickup']}")
    st.write(f"**Destination:** {config['destination']}")
    st.write(f"**Blocked roads:** {len(config['blocked'])}")
    st.write(f"**Traffic cells:** {len(config['traffic_costs'])}")
    st.write(f"**Fare if successful:** £{config['fare']}")

sim = st.session_state.sim
status_text = simulation_status(sim)
perf: Performance = sim["perf"]
kpis = make_kpis(sim, config)

c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card("Simulation Status", status_text, "Auto-updates as the taxi moves")
with c2:
    metric_card("Trip Score", str(perf.score), "Utility after rewards and penalties")
with c3:
    metric_card("Steps Taken", str(perf.steps), "Movement actions completed so far")
with c4:
    metric_card("Weighted Cost", str(perf.path_cost), "Travel cost including traffic")

left, right = st.columns([1.6, 1])
with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Live Route Map")
    st.caption("The taxi moves one step at a time. Numbered circles show when each visited cell was first reached.")
    st.markdown(render_grid(sim, config), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Live Service Status")
    st.markdown(
        f'<span class="status-pill {status_class(status_text)}">{status_text}</span>',
        unsafe_allow_html=True,
    )
    st.write(f"**Taxi location:** {sim['agent'].location}")
    st.write(f"**Current goal:** {sim['current_goal']}")
    st.write(f"**Passenger onboard:** {'Yes' if sim['agent'].has_passenger else 'No'}")
    st.write(f"**Passenger delivered:** {'Yes' if sim['agent'].env.passenger.delivered else 'No'}")
    st.write(f"**Last action:** {sim['last_action'] or 'No action yet'}")
    st.write(f"**Last reason:** {sim['last_reason']}")
    st.progress(int(kpis["progress"]))
    st.caption(f"Trip completion progress: {int(kpis['progress'])}%")
    st.markdown('</div>', unsafe_allow_html=True)

r1, r2, r3, r4 = st.columns(4)
with r1:
    metric_card("Estimated Revenue", f"£{int(kpis['fare'])}", "Fare captured only after successful drop-off")
with r2:
    metric_card("Operating Cost", f"£{int(kpis['operating_cost'])}", "Base cost + path cost + penalties")
with r3:
    metric_card("Estimated Profit", f"£{int(kpis['profit'])}", "Revenue minus operating cost")
with r4:
    metric_card("Trust Score", f"{int(kpis['trust'])}%", "Raised by visible explanations")

log_col, audit_col = st.columns([1.2, 1])
with log_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Decision Explanation")
    st.markdown(f'<div class="log-box">{sim["last_reason"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with audit_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Trip Audit Log")
    recent = "\n".join(f"• {line}" for line in sim["events"][-8:])
    st.markdown(f'<div class="log-box">{recent}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with st.expander("Open full event table"):
    st.dataframe(event_table(sim), use_container_width=True, hide_index=True)

with st.expander("Open technical state"):
    tech = {
        "percepts": sim["agent"].perceive(),
        "replans": perf.replans,
        "invalid_attempts": perf.invalid_attempts,
        "goal_achieved": perf.goal_achieved,
        "trace": sim["trace"],
        "action_log": perf.action_log,
    }
    st.json(tech)

if st.session_state.get("autoplay", False) and not sim["completed"] and not sim["failed"]:
    perform_step(sim)
    time.sleep(st.session_state.get("speed", 0.7))
    st.rerun()
