CyberRangeX

> Simulate. Detect. Defend.

CyberRangeX is an **Automated Attack Simulation & Defense Validation Platform** — a fully dockerized cyber range that launches real attack scenarios against isolated targets, captures detection events, and validates your defensive controls.

---

## Quick Start

```bash
git clone https://github.com/yourusername/cyberrangex.git
cd cyberrangex
docker-compose up -d
cd backend && uvicorn app.main:app --reload
```

API live at → `http://localhost:8000/docs`

---

##  What It Does

```
You trigger a simulation
        ↓
Attacker container launches the attack
        ↓
Target container receives it
        ↓
Suricata + Wazuh detect the activity
        ↓
Events flow into Elasticsearch
        ↓
Results appear live on your dashboard
```

---

##  Attack Scenarios

```
┌─────────────────────┬──────────────────────────┬────────────┐
│ Scenario            │ MITRE Technique          │ Tool       │
├─────────────────────┼──────────────────────────┼────────────┤
│ SSH Brute Force     │ T1110 - Brute Force      │ Hydra      │
│ Port Scan           │ T1046 - Network Discovery│ Nmap       │
│ Password Spray      │ T1110.003 - Spray        │ Hydra      │
│ SQL Injection       │ T1190 - Exploit Public   │ SQLMap     │
│ DNS Exfiltration    │ T1048 - Exfil Over DNS   │ Custom     │
└─────────────────────┴──────────────────────────┴────────────┘
```

---

##  Infrastructure

```
docker-compose up
│
├── attacker        → Kali Linux (Hydra, Nmap, SQLMap)
├── linux_target    → Ubuntu SSH + Wazuh Agent
├── web_target      → DVWA (Damn Vulnerable Web App)
├── suricata        → Network IDS
├── elasticsearch   → Event storage & search
└── postgres        → Platform database
```

---

##  Project Structure

```
cyberrangex/
├── backend/
│   └── app/
│       ├── api/          # auth, scenarios, simulations, health
│       ├── core/         # config, database, JWT
│       ├── models/       # 8 SQLAlchemy tables
│       ├── schemas/      # Pydantic models
│       └── services/     # SimulationService, SearchService
├── simulations/          # Attack scenario engine
│   ├── base_scenario.py
│   ├── ssh_bruteforce.py
│   ├── port_scan.py
│   ├── password_spray.py
│   ├── sql_injection.py
│   └── dns_exfiltration.py
├── cyber_range/          # Docker containers
├── frontend/             # React + Vite dashboard
└── docker-compose.yml
```

---

##  Tech Stack

```
Backend      →  Python · FastAPI · SQLAlchemy · Alembic
Database     →  PostgreSQL
Search       →  Elasticsearch
Frontend     →  React · Vite
Containers   →  Docker · Docker Compose
Attack Tools →  Hydra · Nmap · SQLMap
Detection    →  Suricata · Wazuh
Auth         →  JWT · bcrypt
```

---

##  Key API Endpoints

```http
POST   /auth/register              # Register user
POST   /auth/login                 # Get JWT token
GET    /scenarios/                 # List attack scenarios
POST   /simulations/               # Create simulation
POST   /simulations/{id}/start     # Launch attack
GET    /simulations/{id}/status    # Check progress
WS     /ws/simulations/{id}        # Live event stream
```

---

##  Data Models

| Model | Purpose |
|---|---|
| User | Authentication & RBAC |
| AttackScenario | Scenario definitions & MITRE mappings |
| Simulation | Run history & status tracking |
| DetectionEvent | Events captured during simulations |
| DefenseResult | Defensive control validation outcomes |
| MitreMapping | ATT&CK tactic & technique references |
| Report | Generated simulation reports |
| RiskAssessment | Risk scoring per simulation |

---

##  Screenshots

> *(Add your dashboard screenshots here)*

---

##  Roadmap

- [ ] Full analytics dashboard (Phase 2)
- [ ] Additional scenarios — Ransomware, Lateral Movement, Privilege Escalation
- [ ] PDF report export
- [ ] Multi-user simulation support
- [ ] Threat intelligence feed integration

---

##  Disclaimer

CyberRangeX is built strictly for **educational and research purposes** in isolated lab environments. All simulations run inside Docker containers. Never use attack tools against systems without explicit written authorization.
