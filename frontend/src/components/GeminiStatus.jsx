// Gemini connection status icon.
// Polls /api/gemini/status every few seconds and shows a colored dot + label.

import React, { useEffect, useState } from 'react';
import { checkGeminiStatus } from '../lib/api.js';

export default function GeminiStatus({ backend, serverUrl }) {
  const [status, setStatus] = useState({ configured: false, connected: false, reason: 'checking...' });
  const [checking, setChecking] = useState(false);

  const refresh = async () => {
    setChecking(true);
    const s = await checkGeminiStatus({ serverUrl });
    setStatus(s);
    setChecking(false);
  };

  useEffect(() => {
    refresh();
    // Poll every 20 seconds while Gemini is selected
    if (backend !== 'gemini') return;
    const id = setInterval(refresh, 20000);
    return () => clearInterval(id);
  }, [backend, serverUrl]);

  // Only show status when Gemini backend is selected
  if (backend !== 'gemini') return null;

  let color = '#98a4c2';
  let icon = '○';
  let label = 'checking';
  if (checking) {
    color = '#ffce5c'; icon = '◐'; label = 'checking...';
  } else if (!status.configured) {
    color = '#ff6f6f'; icon = '✕'; label = 'no API key';
  } else if (status.connected) {
    color = '#7ee787'; icon = '●'; label = `Gemini connected (${status.model || 'gemini'})`;
  } else {
    color = '#ff6f6f'; icon = '●'; label = `Gemini offline (${status.reason || 'error'})`;
  }

  return (
    <div
      className="gemini-status"
      title={`Gemini API status — ${label}`}
      onClick={refresh}
    >
      <span className="dot" style={{ color, textShadow: `0 0 8px ${color}` }}>{icon}</span>
      <span className="label">{label}</span>
      <span className="refresh">↻</span>
    </div>
  );
}
