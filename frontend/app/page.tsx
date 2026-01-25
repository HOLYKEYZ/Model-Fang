"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Play, ShieldAlert, Cpu, Activity, Lock, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";

// Types
interface Model {
  id: string;
  name: string;
  provider: string;
}

interface LogEntry {
  timestamp: string;
  message: string;
  type: 'info' | 'error' | 'success';
}

export default function Dashboard() {
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [selectedAttack, setSelectedAttack] = useState("template:standard");
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState("IDLE");
  const [score, setScore] = useState<number | null>(null);

  const logsEndRef = useRef<HTMLDivElement>(null);

  // Fetch models on load
  useEffect(() => {
    fetch('http://localhost:5000/api/models')
      .then(res => res.json())
      .then(data => {
        if (data.targets) setModels(data.targets);
      })
      .catch(err => addLog(`Failed to load models: ${err}`, 'error'));
      
    addLog("System initialized. Ready for Red Teaming.", 'info');
  }, []);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const addLog = (msg: string, type: 'info'|'error'|'success' = 'info') => {
    setLogs(prev => [...prev, {
      timestamp: new Date().toLocaleTimeString(),
      message: msg,
      type
    }]);
  };

  const handleRun = async () => {
    if (!selectedModel) {
      addLog("Select a target model first.", 'error');
      return;
    }

    setIsRunning(true);
    setStatus("RUNNING");
    setScore(null);
    setLogs([]); // Clear logs for new run
    addLog(`Initiating attack: ${selectedAttack} -> ${selectedModel}...`, 'info');

    try {
      const res = await fetch('http://localhost:5000/api/attack', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
           model_id: selectedModel,
           attack_id: selectedAttack,
           context: { source: "dashboard" }
        })
      });

      const data = await res.json();
      const jobId = data.job_id;
      
      addLog(`Job started: ${jobId}`, 'info');

      // Poll for status
      const interval = setInterval(async () => {
        const check = await fetch(`http://localhost:5000/api/jobs/${jobId}`);
        const jobData = await check.json();
        
        if (jobData.status === 'completed' || jobData.status === 'failed') {
          clearInterval(interval);
          setIsRunning(false);
          setStatus(jobData.status.toUpperCase());
          
          if (jobData.status === 'completed') {
            const result = jobData.result;
            setScore(result.success_score);
            addLog(`Execution completed. Score: ${result.success_score.toFixed(2)}`, 'success');
            // Mock transcript replay from result
            result.step_results?.forEach((step: any) => {
               addLog(`[STEP ${step.step_id}] ${step.success ? 'PASSED' : 'FAILED'} - ${step.evaluation?.reasoning || 'No Eval'}`, step.success ? 'success' : 'error');
            });
          } else {
             addLog(`Attack failed: ${jobData.error}`, 'error');
          }
        }
      }, 1000);

    } catch (err) {
      addLog(`API Connection Error: ${err}`, 'error');
      setIsRunning(false);
      setStatus("ERROR");
    }
  };

  return (
    <div className="min-h-screen bg-black text-white p-6 grid grid-cols-1 lg:grid-cols-4 gap-6 font-mono">
      {/* Sidebar / Config */}
      <div className="lg:col-span-1 border-r border-gray-800 pr-6">
        <header className="mb-8 flex items-center space-x-3">
            <img src="/logo.png" alt="Logo" className="w-12 h-12" />
            <div>
                 <h1 className="text-2xl font-bold tracking-tighter text-red-500">MODELFANG</h1>
                 <p className="text-xs text-gray-500">v0.4.0 ANALYST DASHBOARD</p>
            </div>
        </header>
        
        <div className="space-y-6">
            <div className="bg-gray-900 p-4 rounded border border-gray-800">
                <h3 className="text-sm text-gray-400 mb-2 flex items-center"><Cpu size={16} className="mr-2"/> Target Model</h3>
                <select 
                    className="w-full bg-black border border-gray-700 p-2 rounded text-sm focus:border-red-500 outline-none"
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    disabled={isRunning}
                >
                    <option value="">Select Target...</option>
                    {models.map(m => (
                        <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                </select>
            </div>

            <div className="bg-gray-900 p-4 rounded border border-gray-800">
                <h3 className="text-sm text-gray-400 mb-2 flex items-center"><ShieldAlert size={16} className="mr-2"/> Attack Strategy</h3>
                <select 
                    className="w-full bg-black border border-gray-700 p-2 rounded text-sm focus:border-red-500 outline-none mb-2"
                    value={selectedAttack}
                    onChange={(e) => setSelectedAttack(e.target.value)}
                    disabled={isRunning}
                >
                    <option value="template:standard">Standard 6-Layer Jailbreak</option>
                    <option value="template:roles">Roleplay Escalation</option>
                    <option value="template:logic">Logical Paradox</option>
                </select>
                <p className="text-xs text-gray-500">
                    Configuration loaded from /config/attacks.yaml
                </p>
            </div>

            <button
                onClick={handleRun}
                disabled={isRunning}
                className={`w-full py-4 text-center font-bold tracking-widest rounded transition-all flex items-center justify-center
                    ${isRunning 
                        ? 'bg-gray-800 text-gray-500 cursor-not-allowed' 
                        : 'bg-red-600 hover:bg-red-700 text-white shadow-[0_0_15px_rgba(220,38,38,0.5)]'
                    }`}
            >
                {isRunning ? <RefreshCw className="animate-spin mr-2"/> : <Play className="mr-2"/>}
                {isRunning ? 'EXECUTING...' : 'LAUNCH ATTACK'}
            </button>
            
            {score !== null && (
                 <div className="mt-6 p-4 border border-gray-800 bg-gray-900 rounded text-center">
                    <h4 className="text-xs text-gray-400 uppercase">Success Score</h4>
                    <div className={`text-4xl font-bold mt-2 ${score > 0.7 ? 'text-red-500' : 'text-gray-500'}`}>
                        {score.toFixed(2)}
                    </div>
                 </div>
            )}
        </div>
      </div>

      {/* Main Content / Monitor */}
      <div className="lg:col-span-3 flex flex-col h-[90vh]">
         {/* Top Stats */}
         <div className="grid grid-cols-4 gap-4 mb-6">
            <StatsCard label="STATUS" value={status} icon={<Activity/>} active={status === 'RUNNING'} />
            <StatsCard label="ADAPTER" value={selectedModel ? "CONNECTED" : "WAITING"} icon={<Cpu/>} />
            <StatsCard label="SECURITY" value="ACTIVE" icon={<Lock/>} />
            <StatsCard label="TURNS" value={logs.length > 0 ? "LIVE" : "-"} icon={<Terminal/>} />
         </div>

         {/* Console */}
         <div className="flex-1 bg-black border border-gray-800 rounded-lg p-4 overflow-hidden flex flex-col relative shadow-inner">
             <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-red-900 to-transparent opacity-50"></div>
             <div className="flex justify-between items-center mb-4 border-b border-gray-800 pb-2">
                 <h2 className="text-sm font-bold text-gray-400 flex items-center">
                    <Terminal size={16} className="mr-2 text-red-500"/>
                    EXECUTION TRANSCRIPT
                 </h2>
                 <div className="flex space-x-2">
                    <span className="w-3 h-3 rounded-full bg-red-500 opacity-50"></span>
                    <span className="w-3 h-3 rounded-full bg-yellow-500 opacity-50"></span>
                    <span className="w-3 h-3 rounded-full bg-green-500 opacity-50"></span>
                 </div>
             </div>
             
             <div className="flex-1 overflow-y-auto space-y-2 font-mono text-sm p-2 custom-scrollbar">
                 {logs.length === 0 && (
                    <div className="text-gray-600 text-center mt-20 italic">
                        System Ready. Awaiting execution command.
                    </div>
                 )}
                 {logs.map((log, i) => (
                    <motion.div 
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        key={i} 
                        className={`flex items-start space-x-3 p-1 rounded hover:bg-gray-900/50 
                            ${log.type === 'error' ? 'text-red-400' : 
                              log.type === 'success' ? 'text-green-400' : 'text-gray-300'}`}
                    >
                        <span className="text-gray-600 text-xs mt-1 min-w-[60px]">{log.timestamp}</span>
                        <span>{log.message}</span>
                    </motion.div>
                 ))}
                 <div ref={logsEndRef}/>
             </div>
         </div>
      </div>
    </div>
  );
}

function StatsCard({label, value, icon, active}: any) {
    return (
        <div className={`p-4 rounded border flex items-center justify-between ${active ? 'bg-red-900/20 border-red-900' : 'bg-gray-900/30 border-gray-800'}`}>
            <div>
                <p className="text-xs text-gray-500 font-bold mb-1">{label}</p>
                <p className={`text-lg font-bold ${active ? 'text-red-400' : 'text-white'}`}>{value}</p>
            </div>
            <div className={`${active ? 'text-red-500' : 'text-gray-600'}`}>
                {icon}
            </div>
        </div>
    )
}
