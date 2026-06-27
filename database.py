"""
CyberRangeX – Database Layer (SQLite)
Handles all database initialization and connection management.
"""

import sqlite3
import os
from datetime import datetime
import json

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'cyberrangex.db')


def get_db():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    """Initialize the database schema."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
        -- ─────────────────────────────────────────────────────────
        --  Attack Simulations
        -- ─────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS simulations (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            attack_id        TEXT NOT NULL,
            attack_name      TEXT NOT NULL,
            attack_category  TEXT,
            status           TEXT DEFAULT 'pending',
            severity         TEXT,
            target           TEXT,
            started_at       TEXT,
            completed_at     TEXT,
            success          INTEGER DEFAULT 0,
            detected         INTEGER DEFAULT 0,
            detection_time   REAL,
            response_time    REAL,
            steps_completed  INTEGER DEFAULT 0,
            total_steps      INTEGER DEFAULT 0,
            risk_score       REAL DEFAULT 0,
            mitre_techniques TEXT,
            results          TEXT,
            created_at       TEXT DEFAULT (datetime('now'))
        );

        -- ─────────────────────────────────────────────────────────
        --  Security Events / Audit Log
        -- ─────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS events (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            simulation_id  INTEGER REFERENCES simulations(id),
            event_type     TEXT,
            message        TEXT,
            severity       TEXT DEFAULT 'info',
            source_ip      TEXT,
            dest_ip        TEXT,
            technique      TEXT,
            timestamp      TEXT DEFAULT (datetime('now'))
        );

        -- ─────────────────────────────────────────────────────────
        --  Defense Control Results
        -- ─────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS defense_results (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            simulation_id   INTEGER REFERENCES simulations(id),
            control_name    TEXT,
            control_type    TEXT,
            triggered       INTEGER DEFAULT 0,
            alert_generated INTEGER DEFAULT 0,
            blocked         INTEGER DEFAULT 0,
            false_positive  INTEGER DEFAULT 0,
            response_time   REAL,
            confidence      REAL DEFAULT 0,
            timestamp       TEXT DEFAULT (datetime('now'))
        );

        -- ─────────────────────────────────────────────────────────
        --  Generated Reports
        -- ─────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS reports (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT,
            report_type     TEXT,
            status          TEXT DEFAULT 'generating',
            content_json    TEXT,
            simulation_ids  TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        -- ─────────────────────────────────────────────────────────
        --  AI Risk Assessments
        -- ─────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS ai_assessments (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            overall_risk      REAL,
            risk_level        TEXT,
            attack_patterns   TEXT,
            high_risk_paths   TEXT,
            recommendations   TEXT,
            weaknesses        TEXT,
            created_at        TEXT DEFAULT (datetime('now'))
        );
    ''')

    conn.commit()
    conn.close()
    print(f"[DB] Database initialized at: {DB_PATH}")


def seed_demo_data():
    """Seed the database with realistic demo data if empty."""
    conn = get_db()
    cursor = conn.cursor()

    # Check if we already have data
    cursor.execute("SELECT COUNT(*) FROM simulations")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    import random
    from datetime import datetime, timedelta

    attacks = [
        ("brute_force", "Brute Force Attack", "Credential Access", "High", 8.5),
        ("password_spray", "Password Spraying", "Credential Access", "High", 7.8),
        ("phishing", "Phishing Simulation", "Initial Access", "Critical", 9.2),
        ("port_scan", "Port Scanning", "Discovery", "Medium", 5.0),
        ("web_attack", "Web Application Attack", "Initial Access", "High", 8.0),
        ("privilege_esc", "Privilege Escalation", "Privilege Escalation", "Critical", 9.0),
        ("lateral_move", "Lateral Movement", "Lateral Movement", "High", 8.3),
        ("data_exfil", "Data Exfiltration", "Exfiltration", "Critical", 9.5),
        ("dos_attack", "Denial-of-Service", "Impact", "High", 7.5),
    ]

    targets = ["Web Server (192.168.1.50)", "Auth Server (192.168.1.10)",
               "DB Server (192.168.1.20)", "Mail Server (192.168.1.30)",
               "Admin Panel (192.168.1.100)"]

    now = datetime.now()

    for i in range(25):
        attack = random.choice(attacks)
        success = random.random() > 0.4
        detected = random.random() > 0.3
        start = now - timedelta(hours=random.randint(1, 72))
        end = start + timedelta(minutes=random.randint(3, 20))

        cursor.execute('''
            INSERT INTO simulations
            (attack_id, attack_name, attack_category, status, severity, target, started_at,
             completed_at, success, detected, detection_time, response_time,
             steps_completed, total_steps, risk_score, mitre_techniques)
            VALUES (?, ?, ?, 'completed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            attack[0], attack[1], attack[2],
            attack[3],
            random.choice(targets),
            start.isoformat(), end.isoformat(),
            1 if success else 0,
            1 if detected else 0,
            round(random.uniform(5, 45), 1) if detected else None,
            round(random.uniform(10, 90), 1) if detected else None,
            random.randint(3, 7), random.randint(5, 8),
            attack[4],
            json.dumps(["T1110", "T1078"]) if random.random() > 0.5 else json.dumps(["T1566", "T1059"])
        ))

        sim_id = cursor.lastrowid

        # Seed defense results
        controls = [
            ("Firewall", "network"), ("IDS/IPS", "network"),
            ("SIEM", "monitoring"), ("EDR", "endpoint"), ("WAF", "application")
        ]
        for ctrl in controls:
            trig = random.random() > 0.4
            cursor.execute('''
                INSERT INTO defense_results
                (simulation_id, control_name, control_type, triggered, alert_generated,
                 blocked, false_positive, response_time, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sim_id, ctrl[0], ctrl[1],
                1 if trig else 0,
                1 if trig and random.random() > 0.3 else 0,
                1 if trig and random.random() > 0.5 else 0,
                1 if random.random() > 0.9 else 0,
                round(random.uniform(0.5, 25), 1) if trig else None,
                round(random.uniform(60, 99), 1)
            ))

        # Seed events
        messages = [
            ("connection_attempt", f"Connection attempt to {random.choice(targets)}", "info"),
            ("auth_failure", "Multiple authentication failures detected", "high"),
            ("port_scan", "Port scan detected from 10.0.0.5", "medium"),
            ("alert_triggered", "IDS alert: Suspicious traffic pattern", "high"),
            ("blocked", "Traffic blocked by firewall rule", "low"),
        ]
        for _ in range(random.randint(3, 8)):
            msg = random.choice(messages)
            cursor.execute('''
                INSERT INTO events (simulation_id, event_type, message, severity, source_ip, dest_ip)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                sim_id, msg[0], msg[1], msg[2],
                f"10.{random.randint(0,5)}.{random.randint(0,255)}.{random.randint(1,254)}",
                f"192.168.1.{random.randint(1,200)}"
            ))

    conn.commit()
    conn.close()
    print("[DB] Demo data seeded successfully.")
