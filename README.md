# Smart Taxi AI Dashboard

An explainable, traffic-aware Smart Taxi AI system with a live Streamlit dashboard, route planning, passenger pickup/drop-off simulation, and business-oriented performance metrics.

## Overview

This project presents an intelligent taxi agent operating in a simplified grid-based London environment. The system models how an AI taxi can perceive its environment, plan routes, pick up passengers, avoid blocked roads and traffic-heavy areas, deliver passengers to their destination, and explain its decisions.

The project goes beyond a basic academic agent by adding:

- live simulation
- explainable decision-making
- business-oriented performance metrics
- a user-friendly Streamlit dashboard

## Key Features

- Grid-based taxi environment
- Passenger pickup and destination handling
- Traffic-aware and blocked-road-aware navigation
- Rational route planning using search
- Explainable movement decisions
- Live dashboard simulation in Streamlit
- Automatic score and trip metric updates
- Business-oriented dashboard metrics such as revenue, operating cost, and estimated profit

## AI Concepts Demonstrated

This project demonstrates core AI agent design concepts:

- Environment modeling
- Percepts and actions
- Goal-based behavior
- Utility and performance measurement
- Search-based decision-making
- Rational agent behavior
- Explainability

## Tech Stack

- Python
- Streamlit
- Pandas

## Project Files

- `taxiagent_perfect.py`  
  Core taxi agent logic, environment model, search, scoring, and explainability

- `taxi_dashboard_live.py`  
  Live Streamlit dashboard for simulation, route visualization, and business metrics

- `requirements.txt`  
  Python dependencies

- `.gitignore`  
  Standard Python and local environment ignore rules

## How to Run

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/smart-taxi-ai-dashboard.git
cd smart-taxi-ai-dashboard
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

If needed, use:

```bash
py -m pip install -r requirements.txt
```

### 3. Run the live dashboard

```bash
streamlit run taxi_dashboard_live.py
```

If `streamlit` is not recognized, use:

```bash
py -m streamlit run taxi_dashboard_live.py
```

## Example Scenarios

The system can simulate multiple scenarios such as:

- Standard pickup and delivery
- Traffic-aware route selection
- Detour around blocked roads
- Dynamic route execution with live score updates

## Dashboard Modes

The interface is designed for multiple perspectives:

### Business Dashboard
Shows:
- trip score
- weighted route cost
- estimated revenue
- estimated operating cost
- estimated profit
- service success rate

### Passenger View
Shows:
- current taxi progress
- pickup and destination progress
- route transparency
- service completion state

### Technical View
Shows:
- route-planning behavior
- search-based decision logic
- movement explanation
- blocked road and traffic handling

## Business Value

This project can be interpreted as a prototype for an intelligent urban mobility decision-support system.

Potential benefits:
- improved route efficiency
- reduced unnecessary travel
- better customer transparency
- improved service trust through explainability
- useful operational metrics for taxi businesses

## Why This Project Is Different

This is not just a pathfinding script.

It combines:
- AI agent design
- route optimization
- explainable AI
- simulation
- dashboard visualization
- business-oriented thinking


## Author

Paras@s

## Usage Notice

This project is shared for portfolio, and review purposes only.  
Reuse, redistribution, or modification of the code is not permitted without the author's permission.
