"""
CyberRangeX – Main Flask Application
REST API server for the Automated Attack Simulation & Defense Validation Platform.
"""

import os
import sys
import json
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request, Response, stream_with_context
from flask_cors import CORS

# ── Path setup ────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from database import init_db, seed_demo_data
from modules.attack_engine     import AttackEngine
from modules.defense_validator import DefenseValidator
from modules.mitre_mapper      import MitreMapper
from modules.ai_assessor       import AIAssessor
from modules.report_generator  import ReportGenerator

# ── App init ──────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)
app.config['JSON_SORT_KEYS'] = False

# ── Module instances ──────────────────────────────────────────────
engine    = AttackEngine()
validator = DefenseValidator()
mapper    = MitreMapper()
assessor  = AIAssessor()
reporter  = ReportGenerator()


# ══════════════════════════════════════════════════════════════════
#  FRONTEND
# ══════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')


# ══════════════════════════════════════════════════════════════════
#  DASHBOARD API
# ══════════════════════════════════════════════════════════════════

@app.route('/api/dashboard/stats')
def dashboard_stats():
    try:
        stats = engine.get_dashboard_stats()
        def_metrics = validator.get_overall_metrics()
        coverage = mapper.get_coverage_stats()
        stats.update({
            'coverage_score':   def_metrics.get('coverage_score', 0),
            'avg_response_time': def_metrics.get('avg_response_time', 0),
            'mitre_coverage':   coverage.get('coverage_percent', 0),
            'total_techniques': coverage.get('total_techniques', 0),
        })
        return jsonify({'status': 'ok', 'data': stats})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/dashboard/timeline')
def dashboard_timeline():
    try:
        days = int(request.args.get('days', 7))
        data = engine.get_timeline_data(days)
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/dashboard/category-stats')
def category_stats():
    try:
        data = engine.get_attack_category_stats()
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ══════════════════════════════════════════════════════════════════
#  ATTACK SIMULATION API
# ══════════════════════════════════════════════════════════════════

@app.route('/api/attacks')
def list_attacks():
    try:
        attacks = engine.get_attacks()
        return jsonify({'status': 'ok', 'data': attacks})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/attacks/<attack_id>')
def get_attack(attack_id):
    try:
        attack = engine.get_attack(attack_id)
        if not attack:
            return jsonify({'status': 'error', 'message': 'Attack not found'}), 404
        return jsonify({'status': 'ok', 'data': attack})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/attacks/launch', methods=['POST'])
def launch_attack():
    try:
        body = request.get_json() or {}
        attack_id = body.get('attack_id')
        if not attack_id:
            return jsonify({'status': 'error', 'message': 'attack_id required'}), 400

        config = {
            'target':     body.get('target'),
            'intensity':  body.get('intensity', 'medium'),
            'stealth':    body.get('stealth', False),
        }

        sim_id, err = engine.launch_simulation(attack_id, config)
        if err:
            return jsonify({'status': 'error', 'message': err}), 400

        return jsonify({
            'status': 'ok',
            'message': 'Simulation launched successfully',
            'simulation_id': sim_id,
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/attacks/active')
def active_attacks():
    try:
        data = engine.get_active_simulations()
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/attacks/history')
def attack_history():
    try:
        limit = int(request.args.get('limit', 50))
        data = engine.get_simulation_history(limit)
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/attacks/simulation/<int:sim_id>')
def get_simulation(sim_id):
    try:
        sim = engine.get_simulation(sim_id)
        if not sim:
            return jsonify({'status': 'error', 'message': 'Simulation not found'}), 404
        events = engine.get_events(sim_id=sim_id, limit=50)
        defense = validator.get_results_by_simulation(sim_id)
        return jsonify({
            'status': 'ok',
            'data': {'simulation': sim, 'events': events, 'defense_results': defense}
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ══════════════════════════════════════════════════════════════════
#  EVENTS / REAL-TIME FEED
# ══════════════════════════════════════════════════════════════════

@app.route('/api/events')
def get_events():
    try:
        sim_id = request.args.get('sim_id')
        limit  = int(request.args.get('limit', 100))
        data   = engine.get_events(sim_id=sim_id, limit=limit)
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/events/stream')
def event_stream():
    """Server-Sent Events for real-time dashboard updates."""
    def generate():
        last_id = 0
        while True:
            try:
                from database import get_db
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT * FROM events WHERE id > ? ORDER BY id ASC LIMIT 10',
                    (last_id,)
                )
                rows = [dict(r) for r in cursor.fetchall()]
                conn.close()

                if rows:
                    last_id = rows[-1]['id']
                    data = json.dumps(rows)
                    yield f"data: {data}\n\n"
                else:
                    yield f"data: []\n\n"

                time.sleep(2)
            except GeneratorExit:
                break
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(5)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


# ══════════════════════════════════════════════════════════════════
#  DEFENSE VALIDATION API
# ══════════════════════════════════════════════════════════════════

@app.route('/api/defense/metrics')
def defense_metrics():
    try:
        data = validator.get_overall_metrics()
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/defense/controls')
def defense_controls():
    try:
        data = validator.get_control_breakdown()
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/defense/gaps')
def detection_gaps():
    try:
        data = validator.get_detection_gaps()
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/defense/trend')
def defense_trend():
    try:
        data = validator.get_trend_data()
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/defense/recent')
def defense_recent():
    try:
        limit = int(request.args.get('limit', 20))
        data = validator.get_recent_results(limit)
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ══════════════════════════════════════════════════════════════════
#  MITRE ATT&CK API
# ══════════════════════════════════════════════════════════════════

@app.route('/api/mitre/framework')
def mitre_framework():
    try:
        data = mapper.get_framework()
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/mitre/heatmap')
def mitre_heatmap():
    try:
        data = mapper.get_heatmap_data()
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/mitre/coverage')
def mitre_coverage():
    try:
        data = mapper.get_coverage_stats()
        tactic_cov = mapper.get_tactic_coverage()
        return jsonify({'status': 'ok', 'data': data, 'tactic_coverage': tactic_cov})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/mitre/map/<attack_id>')
def mitre_map_attack(attack_id):
    try:
        data = mapper.map_attack(attack_id)
        if not data:
            return jsonify({'status': 'error', 'message': 'Attack not found'}), 404
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ══════════════════════════════════════════════════════════════════
#  AI RISK ASSESSMENT API
# ══════════════════════════════════════════════════════════════════

@app.route('/api/ai/assessment')
def ai_assessment():
    try:
        data = assessor.get_latest_assessment()
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/ai/run-assessment', methods=['POST'])
def run_ai_assessment():
    try:
        data = assessor.run_assessment()
        return jsonify({'status': 'ok', 'message': 'Assessment complete', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/ai/risk-trend')
def ai_risk_trend():
    try:
        data = assessor.get_risk_trend()
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ══════════════════════════════════════════════════════════════════
#  REPORTS API
# ══════════════════════════════════════════════════════════════════

@app.route('/api/reports')
def list_reports():
    try:
        data = reporter.get_reports()
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/reports/generate', methods=['POST'])
def generate_report():
    try:
        body = request.get_json() or {}
        rtype  = body.get('type', 'full')
        title  = body.get('title')
        sim_ids= body.get('simulation_ids', [])

        report_id, content = reporter.generate_report(rtype, sim_ids, title)
        return jsonify({
            'status': 'ok',
            'message': 'Report generated successfully',
            'report_id': report_id,
            'data': content,
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/reports/<int:report_id>')
def get_report(report_id):
    try:
        report = reporter.get_report(report_id)
        if not report:
            return jsonify({'status': 'error', 'message': 'Report not found'}), 404
        return jsonify({'status': 'ok', 'data': report})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ══════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════════════

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'platform': 'CyberRangeX',
        'version': '2.0.0',
        'timestamp': datetime.now().isoformat(),
    })


# ══════════════════════════════════════════════════════════════════
#  STARTUP
# ══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 60)
    print("  CyberRangeX – Attack Simulation & Defense Validation")
    print("  Version 2.0.0  |  Initializing...")
    print("=" * 60)

    init_db()
    seed_demo_data()

    print("[*] Platform ready at http://127.0.0.1:5050")
    print("[*] Press Ctrl+C to stop\n")
    app.run(debug=True, host='0.0.0.0', port=5050, use_reloader=False, threaded=True)
