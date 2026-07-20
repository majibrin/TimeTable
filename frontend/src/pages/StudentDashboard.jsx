import React, { useState, useEffect, useCallback } from 'react';
import API from '../api/client';
import TimetableGrid from '../components/TimetableGrid';

const DAYS_ORDER = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
const DAY_MAP = { 0: 'SUN', 1: 'MON', 2: 'TUE', 3: 'WED', 4: 'THU', 5: 'FRI', 6: 'SAT' };

function getNextSession(schedules) {
  const now = new Date();
  const todayKey = DAY_MAP[now.getDay()];
  const currentMinutes = now.getHours() * 60 + now.getMinutes();

  // Check today first, then upcoming days
  const orderedDays = [];
  const todayIdx = DAYS_ORDER.indexOf(todayKey);
  if (todayIdx !== -1) {
    for (let i = 0; i < DAYS_ORDER.length; i++) {
      orderedDays.push(DAYS_ORDER[(todayIdx + i) % DAYS_ORDER.length]);
    }
  } else {
    orderedDays.push(...DAYS_ORDER);
  }

  for (const day of orderedDays) {
    const daySessions = schedules
      .filter(s => s.day === day)
      .sort((a, b) => a.start_time.localeCompare(b.start_time));

    for (const session of daySessions) {
      const [h, m] = session.start_time.split(':').map(Number);
      const sessionMinutes = h * 60 + m;
      if (day !== todayKey || sessionMinutes > currentMinutes) {
        // Calculate minutes until
        let daysUntil = (DAYS_ORDER.indexOf(day) - DAYS_ORDER.indexOf(todayKey) + 6) % 6;
        const minutesUntil = daysUntil * 24 * 60 + (sessionMinutes - currentMinutes);
        return { session, minutesUntil, day };
      }
    }
  }
  return null;
}

function Countdown({ minutesUntil }) {
  const [remaining, setRemaining] = useState(minutesUntil * 60);

  useEffect(() => {
    const timer = setInterval(() => setRemaining(r => Math.max(0, r - 1)), 1000);
    return () => clearInterval(timer);
  }, []);

  const h = Math.floor(remaining / 3600);
  const m = Math.floor((remaining % 3600) / 60);
  const s = remaining % 60;

  return (
    <div className="flex gap-3 justify-center mt-2">
      {[['HRS', h], ['MIN', m], ['SEC', s]].map(([label, val]) => (
        <div key={label} className="text-center">
          <div className="text-2xl font-bold text-blue-600 font-mono">{String(val).padStart(2, '0')}</div>
          <div className="text-[9px] text-slate-400 tracking-widest">{label}</div>
        </div>
      ))}
    </div>
  );
}

export default function StudentDashboard() {
  const [schedules, setSchedules] = useState([]);
  const [cohorts, setCohorts] = useState([]);
  const [selectedCohort, setSelectedCohort] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [nextSession, setNextSession] = useState(null);

  const fetchCohorts = async () => {
    try {
      const res = await API.get('cohorts/');
      setCohorts(res.data);
    } catch (e) {
      setError('Failed to load cohorts');
    }
  };

  const fetchTimetable = useCallback(async () => {
    if (!selectedCohort) return;
    setLoading(true);
    try {
      const res = await API.get(`slots/?published=true&cohort=${selectedCohort}`);
      const normalized = res.data.map(slot => ({
        course_code: (slot.course_detail || '').split(' - ')[0],
        room: slot.venue_name || 'TBD',
        lecturer: slot.lecturer_name || 'Unassigned',
        day: (slot.day || 'MON').toUpperCase().substring(0, 3),
        start_time: slot.start_time ? slot.start_time.substring(0, 5) : '08:00',
        duration: parseInt(slot.duration || 1, 10),
      }));
      setSchedules(normalized);
      setNextSession(getNextSession(normalized));
    } catch (e) {
      setError('Failed to load timetable');
    } finally {
      setLoading(false);
    }
  }, [selectedCohort]);

  useEffect(() => { fetchCohorts(); }, []);
  useEffect(() => { fetchTimetable(); }, [fetchTimetable]);

  const handleLogout = () => { localStorage.removeItem('token'); window.location.href = '/login'; };

  return (
    <div className="min-h-screen bg-slate-50 font-mono">
      <div className="bg-white border-b border-slate-200 px-4 py-3 flex justify-between items-center">
        <div>
          <h1 className="text-sm font-bold text-slate-900">STUDENT</h1>
          <p className="text-[10px] text-slate-400">Faculty of Science — GSU</p>
        </div>
        <button onClick={handleLogout} className="px-3 py-1.5 border border-red-200 text-red-600 text-xs font-bold rounded">LOGOUT</button>
      </div>

      <div className="p-4">
        {error && <div className="bg-red-50 text-red-700 text-xs p-3 rounded mb-3 border border-red-200">{error}</div>}

        <div className="bg-white border border-slate-200 rounded-lg p-4 mb-4 shadow-sm">
          <label className="block text-[10px] text-slate-500 mb-1 uppercase">Select Your Department & Level</label>
          <select value={selectedCohort} onChange={e => setSelectedCohort(e.target.value)}
            className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400">
            <option value="">-- Select Cohort --</option>
            {cohorts.map(c => (
              <option key={c.id} value={c.id}>{c.department_name} — {c.level}</option>
            ))}
          </select>
        </div>

        {nextSession && (
          <div className="bg-white border border-blue-200 rounded-lg p-4 mb-4 shadow-sm text-center">
            <div className="text-[10px] text-slate-400 uppercase tracking-widest mb-1">Next Lecture</div>
            <div className="text-sm font-bold text-slate-900">{nextSession.session.course_code}</div>
            <div className="text-xs text-slate-500">{nextSession.day} · {nextSession.session.start_time} · {nextSession.session.room}</div>
            <Countdown minutesUntil={nextSession.minutesUntil} />
          </div>
        )}

        {loading ? (
          <div className="text-center text-xs text-slate-400 py-12">Loading timetable...</div>
        ) : selectedCohort && schedules.length === 0 ? (
          <div className="text-center text-xs text-slate-400 py-12">No published timetable for this cohort yet</div>
        ) : selectedCohort ? (
          <TimetableGrid schedules={schedules} />
        ) : null}
      </div>
    </div>
  );
}
