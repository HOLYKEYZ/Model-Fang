'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { History, CheckCircle, XCircle, Clock, ChevronRight, AlertTriangle, ArrowLeft } from 'lucide-react';

interface AttackSummary {
  id: string;
  name: string;
  status: string;
  success: boolean;
  turns: number;
  max_score: number;
  timestamp: string;
  category: string;
  filename: string;
}

interface AttackDetail {
  attack_id: string;
  attack_name: string;
  status: string;
  success: boolean;
  turns_to_success: number;
  conversation_transcript: Array<{ role: string; content: string }>;
  evaluation_summary: {
    max_score: number;
    avg_score: number;
    scores_per_step: number[];
    steps_evaluated: number;
  };
  timestamp: string;
}

export default function HistoryPage() {
  const [attacks, setAttacks] = useState<AttackSummary[]>([]);
  const [selectedAttack, setSelectedAttack] = useState<AttackDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:5000/api/history')
      .then(res => res.json())
      .then(data => {
        setAttacks(data.attacks || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load history:', err);
        setLoading(false);
      });
  }, []);

  const loadDetail = async (filename: string) => {
    try {
      const res = await fetch(`http://localhost:5000/api/history/${filename}`);
      const data = await res.json();
      setSelectedAttack(data);
    } catch (err) {
      console.error('Failed to load attack detail:', err);
    }
  };

  const formatDate = (timestamp: string) => {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  return (
    <div className="min-h-screen bg-black text-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-gray-500 hover:text-red-500 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <History className="text-red-500" />
            Attack History
          </h1>
        </div>
        <span className="text-gray-600 text-sm">{attacks.length} attacks recorded</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Attack List */}
        <div className="lg:col-span-1 space-y-3">
          {loading ? (
            <div className="text-center py-10 text-gray-500">Loading history...</div>
          ) : attacks.length === 0 ? (
            <div className="text-center py-10 text-gray-500">
              <AlertTriangle className="w-10 h-10 mx-auto mb-3 text-yellow-600" />
              No attacks recorded yet. Run your first attack!
            </div>
          ) : (
            attacks.map((attack) => (
              <div
                key={attack.filename}
                onClick={() => loadDetail(attack.filename)}
                className={`p-4 rounded-lg border cursor-pointer transition-all
                  ${selectedAttack?.attack_id === attack.id 
                    ? 'border-red-500 bg-gray-900' 
                    : 'border-gray-800 bg-gray-950 hover:border-gray-700'}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-sm truncate max-w-[180px]">{attack.name}</span>
                  {attack.success ? (
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-500" />
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <Clock className="w-3 h-3" />
                  {formatDate(attack.timestamp)}
                </div>
                <div className="flex items-center justify-between mt-2">
                  <span className={`text-xs px-2 py-0.5 rounded capitalize
                    ${attack.success ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
                    {attack.status}
                  </span>
                  <span className="text-xs text-gray-600">
                    Score: {(attack.max_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Attack Detail */}
        <div className="lg:col-span-2 bg-gray-950 border border-gray-800 rounded-lg p-6">
          {selectedAttack ? (
            <>
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-xl font-bold text-red-400">{selectedAttack.attack_name}</h2>
                  <p className="text-sm text-gray-500">{selectedAttack.attack_id}</p>
                </div>
                <div className="text-right">
                  <div className={`text-2xl font-bold ${selectedAttack.success ? 'text-green-400' : 'text-red-400'}`}>
                    {selectedAttack.success ? 'JAILBROKEN' : 'BLOCKED'}
                  </div>
                  <div className="text-xs text-gray-500">
                    {selectedAttack.turns_to_success > 0 ? `in ${selectedAttack.turns_to_success} turns` : 'Failed'}
                  </div>
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-900 rounded p-3 text-center">
                  <div className="text-2xl font-bold text-yellow-400">
                    {(selectedAttack.evaluation_summary?.max_score * 100 || 0).toFixed(0)}%
                  </div>
                  <div className="text-xs text-gray-500">Max Score</div>
                </div>
                <div className="bg-gray-900 rounded p-3 text-center">
                  <div className="text-2xl font-bold text-blue-400">
                    {(selectedAttack.evaluation_summary?.avg_score * 100 || 0).toFixed(0)}%
                  </div>
                  <div className="text-xs text-gray-500">Avg Score</div>
                </div>
                <div className="bg-gray-900 rounded p-3 text-center">
                  <div className="text-2xl font-bold text-purple-400">
                    {selectedAttack.evaluation_summary?.steps_evaluated || 0}
                  </div>
                  <div className="text-xs text-gray-500">Steps</div>
                </div>
              </div>

              {/* Transcript */}
              <h3 className="text-sm font-bold text-gray-400 mb-3 uppercase tracking-wider">Conversation Transcript</h3>
              <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
                {selectedAttack.conversation_transcript?.map((msg, i) => (
                  <div key={i} className={`p-4 rounded-lg ${msg.role === 'user' ? 'bg-red-950/30 border-l-2 border-red-500' : 'bg-green-950/30 border-l-2 border-green-500'}`}>
                    <div className="text-xs font-bold mb-2 uppercase tracking-wider text-gray-500">
                      {msg.role === 'user' ? '🔴 Attacker Prompt' : '🟢 Target Response'}
                    </div>
                    <div className="text-sm whitespace-pre-wrap leading-relaxed">
                      {msg.content || <span className="text-gray-600 italic">[No content]</span>}
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-600 py-20">
              <ChevronRight className="w-12 h-12 mb-4" />
              <p>Select an attack to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
