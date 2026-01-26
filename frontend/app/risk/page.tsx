"use client";

import React, { useState, useEffect } from 'react';
import { Shield, AlertTriangle, CheckCircle, XCircle, FileText, Activity } from "lucide-react";
import Link from 'next/link';

export default function RiskDashboard() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch('http://localhost:5000/api/risk')
      .then(res => res.json())
      .then(setData)
      .catch(console.error);
  }, []);

  if (!data) return <div className="p-10 text-white">Loading Risk Matrix...</div>;

  return (
    <div className="min-h-screen bg-black text-white font-mono p-8">
      <header className="mb-8 flex justify-between items-center border-b border-gray-800 pb-4">
        <div>
            <h1 className="text-3xl font-bold flex items-center">
                <Shield className="mr-3 text-red-500" />
                LLM RISK ASSESSMENT
            </h1>
            <p className="text-gray-500 mt-1">OWASP LLM Top 10 & NIST AI RMF Compliance</p>
        </div>
        <Link href="/" className="px-4 py-2 bg-gray-800 rounded hover:bg-gray-700 transition">
            &larr; Back to Console
        </Link>
      </header>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <RiskCard label="CRITICAL" count={data.summary.critical} color="bg-red-500" />
        <RiskCard label="HIGH" count={data.summary.high} color="bg-orange-500" />
        <RiskCard label="MEDIUM" count={data.summary.medium} color="bg-yellow-500" />
        <RiskCard label="LOW" count={data.summary.low} color="bg-green-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Security Risk */}
        <div className="bg-gray-900 rounded p-6 border border-gray-800">
            <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-gray-300">Security Risk</h3>
                <div className="relative w-24 h-24 flex items-center justify-center">
                    <svg className="w-full h-full transform -rotate-90">
                        <circle cx="48" cy="48" r="40" stroke="#333" strokeWidth="8" fill="none" />
                        <circle cx="48" cy="48" r="40" stroke={data.security_score < 70 ? "#ef4444" : "#10b981"} strokeWidth="8" fill="none" 
                            strokeDasharray={251} strokeDashoffset={251 - (251 * data.security_score / 100)} />
                    </svg>
                    <span className="absolute text-xl font-bold">{data.security_score}%</span>
                </div>
            </div>
            
            <div className="space-y-4">
                {data.items.security.map((item: any, i: number) => (
                    <RiskItem key={i} name={item.name} status={item.status} />
                ))}
            </div>
        </div>

        {/* Legal Risk */}
        <div className="bg-gray-900 rounded p-6 border border-gray-800">
            <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-gray-300">Legal Risk</h3>
                <div className="text-right">
                    <p className="text-sm text-gray-500">Compliance</p>
                    <p className="text-2xl font-bold text-blue-400">EU AI Act</p>
                </div>
            </div>
             <div className="space-y-4">
                {data.items.legal.map((item: any, i: number) => (
                    <RiskItem key={i} name={item.name} status={item.status} />
                ))}
            </div>
        </div>
      </div>
    </div>
  );
}

function RiskCard({ label, count, color }: any) {
    return (
        <div className="bg-white text-black rounded p-4 flex flex-col justify-between h-32 relative overflow-hidden">
             <div className={`absolute left-0 top-0 bottom-0 w-2 ${color}`}></div>
             <h4 className="font-bold text-gray-600">{label}</h4>
             <span className="text-4xl font-bold">{count}</span>
             <span className="text-xs text-gray-500">issues detected</span>
        </div>
    )
}

function RiskItem({ name, status }: any) {
    return (
        <div className="flex justify-between items-center p-3 bg-black rounded border border-gray-800">
            <span>{name}</span>
            {status === 'pass' ? 
                <CheckCircle className="text-green-500 w-5 h-5" /> : 
                <XCircle className="text-red-500 w-5 h-5" />
            }
        </div>
    )
}
