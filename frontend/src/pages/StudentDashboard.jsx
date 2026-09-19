import React, { useState, useEffect, useCallback } from 'react';
import API from '../api/client';
import TimetableGrid from '../components/TimetableGrid';
import { exportTimetablePdf } from '../utils/exportPdf';
import { useAuth } from '../context/AuthContext';

const LEVELS = ['100L', '200L', '300L', '400L'];

function slotLevel(slot) {
  return (slot.student_group_detail || slot.cohort_detail || '').match(/\b\d{3}L\b/)?.[0] || '';
}

const DAYS_ORDER = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
const DAY_MAP = { 0: 'SUN', 1: 'MON', 2: 'TUE', 3: 'WED', 4: 'THU', 5: 'FRI', 6: 'SAT' };

function getNextSession(schedules) {
  const now = new Date();
  const todayKey = DAY_MAP[now.getDay()];
  const currentMinutes = now.getHours() * 60 + now.getMinutes();

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
          <div className="text-2xl font-bold text-blue-600 font-sans">{String(val).padStart(2, '0')}</div>
          <div className="text-[9px] text-slate-400 tracking-widest">{label}</div>
        </div>
      ))}
    </div>
  );
}

export default function StudentDashboard() {
  const { user } = useAuth();
  const [schedules, setSchedules] = useState([]);
  const [selectedLevel, setSelectedLevel] = useState('100L');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [nextSession, setNextSession] = useState(null);

  const fetchTimetable = useCallback(async () => {
    if (!user?.department) return;
    setLoading(true);
    try {
      const res = await API.get(`slots/?published=true&student_department=${user.department}&level=${selectedLevel}`);
      const normalized = res.data.map(slot => ({
        course_code: (slot.course_detail || '').split(' - ')[0],
        room: slot.venue_name || 'TBD',
        student_group_detail: slot.student_group_detail,
        level: slotLevel(slot),
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
  }, [selectedLevel, user?.department]);

  useEffect(() => { fetchTimetable(); }, [fetchTimetable]);

  const handleExport = () => {
    exportTimetablePdf(schedules, {
      level: selectedLevel,
      semester: 'FIRST',
      title: `${selectedLevel} FIRST SEMESTER LECTURES TIME TABLE`,
      subtitle: `${selectedLevel} — Faculty of Science, GSU`,
      filename: 'my-class-timetable'
    });
  };

  const handleLogout = () => { localStorage.removeItem('token'); window.location.href = '/login'; };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200/60 px-4 py-3">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="text-sm font-bold text-slate-900">STUDENT</h1>
            <p className="text-[10px] sm:text-xs text-slate-400">Faculty of Science — GSU</p>
          </div>
          <div className="flex gap-2">
            <button onClick={handleExport} disabled={!schedules.length}
              className="px-3 py-1.5 text-[10px] sm:text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-sm">
              EXPORT PDF
            </button>
            <button onClick={handleLogout}
              className="px-3 py-1.5 text-[10px] sm:text-xs font-bold border border-red-300 hover:bg-red-50 text-red-600 rounded transition-colors">
              LOGOUT
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 md:py-6">
        {error && <div className="bg-red-50 text-red-700 text-xs p-3 rounded-xl mb-4 border border-red-200">{error}</div>}

        {/* Level Selector */}
        <div className="bg-white border border-slate-200/60 rounded-2xl p-5 mb-6 shadow-sm">
          <div className="flex flex-wrap gap-2">
            {LEVELS.map(level => (
              <button key={level} onClick={() => setSelectedLevel(level)}
                className={`px-4 py-2 text-[10px] font-bold rounded-lg border ${selectedLevel === level ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-600 border-slate-200'}`}>
                {level}
              </button>
            ))}
          </div>
        </div>

        {/* Next Session Countdown */}
        {nextSession && (
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/60 rounded-2xl p-5 mb-6 shadow-sm">
            <div className="text-center">
              <div className="text-[10px] font-bold text-blue-600 uppercase tracking-widest mb-1">Next Lecture</div>
              <div className="text-base font-black text-slate-900">{nextSession.session.course_code}</div>
              <div className="text-xs font-bold text-slate-500 mt-0.5">
                {nextSession.day} · {nextSession.session.start_time} · {nextSession.session.room}
              </div>
              <Countdown minutesUntil={nextSession.minutesUntil} />
            </div>
          </div>
        )}

        {/* Timetable */}
        {loading ? (
          <div className="text-center text-xs text-slate-400 py-12 bg-white rounded-2xl border border-slate-200/60 p-8">Loading timetable...</div>
        ) : schedules.length === 0 ? (
          <div className="text-center text-xs text-slate-400 py-12 bg-white rounded-2xl border border-slate-200/60 p-8">No published timetable for this level yet</div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200/60 p-4 shadow-sm">
            <TimetableGrid schedules={schedules} />
          </div>
        )}
      </div>
    </div>
  );
}