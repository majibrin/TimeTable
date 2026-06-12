import React, { useState, useEffect } from 'react';
import TimetableGrid from '../components/TimetableGrid';
import API from '../api/client';

export default function Dashboard() {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchTimetableData = async () => {
    try {
      setLoading(true);
      const res = await API.get('slots/');
      const normalizedData = res.data.map(slot => ({
        course_code: (slot.course_detail || '').split(' - ')[0] || `ID: ${slot.course}`,
        room: slot.venue_name || 'Unassigned',
        lecturer: slot.lecturer_name || 'Staff',
        day: (slot.day || 'MON').toUpperCase().substring(0, 3),
        start_time: slot.start_time ? slot.start_time.substring(0, 5) : '08:00',
        duration: parseInt(slot.duration || 1, 10)
      }));
      setSchedules(normalizedData);
      setError('');
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTimetableData();
  }, []);

  const handleGenerate = async () => {
    if (!window.confirm("Confirm: Trigger optimization?")) return;
    try {
      setLoading(true);
      await API.post('generate/', { 
        initial_temperature: 1000.0, 
        cooling_rate: 0.95, 
        min_temperature: 0.01 
      });
      await fetchTimetableData();
    } catch (err) {
      alert("Generation failed: " + err.message);
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    window.location.reload();
  };

  return (
    <div className="min-h-screen bg-slate-50 font-mono p-4">
      <div className="max-w-6xl mx-auto flex justify-between items-center bg-white border border-slate-200 rounded-lg p-4 mb-6 shadow-sm">
        <div>
          <h1 className="text-lg font-bold text-slate-950 tracking-tight">WORKSPACE DASHBOARD</h1>
          <p className="text-xs text-slate-500 font-medium">Data Stream: LIVE_DATABASE_SYNC</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleGenerate} className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded font-bold text-xs tracking-wider transition-colors">
            GENERATE
          </button>
          <button onClick={handleLogout} className="px-3 py-1.5 border border-red-200 hover:bg-red-50 text-red-600 rounded font-bold text-xs tracking-wider transition-colors">
            LOGOUT
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto space-y-6">
        {loading ? (
          <div className="bg-white border border-slate-200 rounded-lg p-12 text-center text-slate-500 text-sm">
            Synchronizing matrix allocations...
          </div>
        ) : error ? (
          <div className="bg-red-50 text-red-700 p-4 rounded-lg border border-red-200 text-xs break-all whitespace-pre-wrap">
            {error}
          </div>
        ) : (
          <TimetableGrid schedules={schedules} />
        )}
      </div>
    </div>
  );
}
