"""
ModelFang API Server

Backend API for the Next.js Dashboard.
"""

import os
import json
import threading
import uuid
import time
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

from modelfang.api import run_attack
from modelfang.config.loader import load_models_config

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

from modelfang.compliance.owasp import ComplianceMapper

# ... (Job Store)

@app.route("/")
def index():
    return jsonify({
        "status": "online",
        "message": "ModelFang Backend API. Frontend is running at http://localhost:3000",
        "endpoints": ["/api/models", "/api/attack", "/api/health", "/api/risk"]
    })

@app.route("/api/risk")
def risk_assessment():
    """Get aggregate risk assessment."""
    # Aggregating from in-memory jobs for real-time view
    # In prod, query DB
    successful_categories = []
    for job in JOBS.values():
        if job["status"] == "completed" and job["result"]:
            # Extract successful steps or categories
            # Simplified: if score > 0.5, mark category 'jailbreak' as success
            if job["result"]["success_score"] > 0.5:
                successful_categories.append("jailbreak") # Default for now
    
    assessment = ComplianceMapper.analyze_risk(successful_categories)
    return jsonify(assessment)

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "version": "0.4.0"})

@app.route("/api/models")
def list_models():
    """List available target models."""
    try:
        models_conf = load_models_config()
        targets = [
            {
                "id": m.model_id, 
                "name": m.model_name, 
                "provider": m.provider,
                "role": m.role
            } 
            for m in models_conf.get_targets()
        ]
        return jsonify({"targets": targets})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/attack", methods=["POST"])
def start_attack():
    """Start an attack execution."""
    data = request.json
    attack_id = data.get("attack_id", "template:standard")
    model_id = data.get("model_id")
    context = data.get("context", {})
    seed = data.get("seed")
    
    if not model_id:
        return jsonify({"error": "model_id is required"}), 400
        
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "id": job_id,
        "status": "pending",
        "result": None,
        "created_at": time.time()
    }
    
    def _run():
        try:
            JOBS[job_id]["status"] = "running"
            result = run_attack(
                attack_id=attack_id,
                target_model_id=model_id,
                context=context,
                seed=seed,
                config_dir=os.environ.get("MODELFANG_CONFIG_DIR")
            )
            JOBS[job_id]["status"] = "completed"
            JOBS[job_id]["result"] = result
        except Exception as e:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = str(e)
            
    thread = threading.Thread(target=_run)
    thread.start()
    
    return jsonify({"job_id": job_id, "status": "pending"})

@app.route("/api/jobs/<job_id>")
def get_job(job_id):
    """Get job status and result."""
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

def start_server(port=5000, debug=True):
    app.run(host="0.0.0.0", port=port, debug=debug)

if __name__ == "__main__":
    start_server()
