import React, { useState, useEffect } from 'react';
import API from '../api/client';
import TimetableGrid from '../components/TimetableGrid';

export default function LecturerDashboard() {
  const [schedules, setSchedules] = useState([]);
  const [slots, setSlots] = useState([]);
  const [venues, setVenues] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('TIMETABLE');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [form, setForm] = useState({ session_slot: '', reason: '', proposed_day: '', proposed_start_time: '', proposed_venue: '' });

  const DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
  const TIMES = ['08:00', '09:00', '10:00', '11:00', '12:00', '14:00', '15:00', '16:00', '17:00'];

  const msg = (ok, text) => {
    if (ok) setSuccess(text); else setError(text);
    setTimeout(() => { setSuccess(''); setError(''); }, 4000);
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const [slotsRes, venuesRes, requestsRes] = await Promise.all([
        API.get('slots/'),
        API.get('venues/'),
        API.get('requests/'),
      ]);
      setSlots(slotsRes.data);
      setVenues(venuesRes.data);
      setRequests(requestsRes.data);
      setSchedules(slotsRes.data.map(slot => ({
        course_code: (slot.course_detail || '').split(' - ')[0],
        room: slot.venue_name || 'TBD',
        lecturer: slot.lecturer_name || 'Unassigned',
        day: (slot.day || 'MON').toUpperCase().substring(0, 3),
        start_time: slot.start_time ? slot.start_time.substring(0, 5) : '08:00',
        duration: parseInt(slot.duration || 1, 10),
      })));
    } catch (e) {
      msg(false, 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleSubmitRequest = async (e) => {
    e.preventDefault();
    try {
      await API.post('requests/', {
        session_slot: parseInt(form.session_slot),
        reason: form.reason,
        proposed_day: form.proposed_day || null,
        proposed_start_time: form.proposed_start_time || null,
        proposed_venue: form.proposed_venue ? parseInt(form.proposed_venue) : null,
      });
      msg(true, 'Request submitted successfully');
      setForm({ session_slot: '', reason: '', proposed_day: '', proposed_start_time: '', proposed_venue: '' });
      fetchData();
    } catch (e) {
      msg(false, 'Failed to submit request');
    }
  };

  const handleLogout = () => { localStorage.removeItem('token'); window.location.href = '/login'; };

  return (
    <div className="min-h-screen bg-slate-50 font-mono">
      <div className="bg-white border-b border-slate-200 px-4 py-3 flex justify-between items-center">
        <div>
          <h1 className="text-sm font-bold text-slate-900">LECTURER</h1>
          <p className="text-[10px] text-slate-400">My Timetable</p>
        </div>
        <button onClick={handleLogout} className="px-3 py-1.5 border border-red-200 text-red-600 text-xs font-bold rounded">LOGOUT</button>
      </div>

      <div className="flex border-b border-slate-200 bg-white px-4">
        {['TIMETABLE', 'REQUEST'].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-[11px] font-bold border-b-2 transition-colors ${tab === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400'}`}>
            {t}
          </button>
        ))}
      </div>

      <div className="p-4">
        {error && <div className="bg-red-50 text-red-700 text-xs p-3 rounded mb-3 border border-red-200">{error}</div>}
        {success && <div className="bg-green-50 text-green-700 text-xs p-3 rounded mb-3 border border-green-200">{success}</div>}

        {tab === 'TIMETABLE' && (
          loading ? <div className="text-center text-xs text-slate-400 py-12">Loading...</div>
          : schedules.length === 0
            ? <div className="text-center text-xs text-slate-400 py-12">No sessions assigned yet</div>
            : <TimetableGrid schedules={schedules} />
        )}

        {tab === 'REQUEST' && (
          <div className="max-w-lg">
            <div className="bg-white border border-slate-200 rounded-lg p-4 mb-4 shadow-sm">
              <h2 className="text-xs font-bold text-slate-700 mb-3 uppercase">Submit Adjustment Request</h2>
              <form onSubmit={handleSubmitRequest} className="space-y-3">
                <div>
                  <label className="block text-[10px] text-slate-500 mb-1">SESSION</label>
                  <select value={form.session_slot} onChange={e => setForm({...form, session_slot: e.target.value})} required
                    className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400">
                    <option value="">-- Select Session --</option>
                    {slots.map(s => (
                      <option key={s.id} value={s.id}>{s.course_detail} — {s.day} {s.start_time?.substring(0,5)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500 mb-1">REASON</label>
                  <textarea value={form.reason} onChange={e => setForm({...form, reason: e.target.value})} required rows={3}
                    className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] text-slate-500 mb-1">PROPOSED DAY (optional)</label>
                    <select value={form.proposed_day} onChange={e => setForm({...form, proposed_day: e.target.value})}
                      className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400">
                      <option value="">-- No change --</option>
                      {DAYS.map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-500 mb-1">PROPOSED TIME (optional)</label>
                    <select value={form.proposed_start_time} onChange={e => setForm({...form, proposed_start_time: e.target.value})}
                      className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400">
                      <option value="">-- No change --</option>
                      {TIMES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500 mb-1">PROPOSED VENUE (optional)</label>
                  <select value={form.proposed_venue} onChange={e => setForm({...form, proposed_venue: e.target.value})}
                    className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400">
                    <option value="">-- No change --</option>
                    {venues.map(v => <option key={v.id} value={v.id}>{v.name} (Cap: {v.capacity})</option>)}
                  </select>
                </div>
                <button type="submit" className="w-full py-2 bg-slate-900 text-white text-xs font-bold rounded hover:bg-slate-700">
                  SUBMIT REQUEST
                </button>
              </form>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg shadow-sm">
              <div className="p-3 border-b border-slate-100 text-xs font-bold text-slate-700">MY REQUESTS ({requests.length})</div>
              {requests.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-400">No requests submitted</div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {requests.map(r => (
                    <div key={r.id} className="p-3">
                      <div className="flex justify-between items-start">
                        <div className="text-xs font-bold text-slate-800">{r.slot_detail}</div>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${r.status === 'PENDING' ? 'bg-amber-50 text-amber-600' : r.status === 'APPROVED' ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'}`}>
                          {r.status}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-500 mt-1">{r.reason}</div>
                      {r.officer_note && <div className="text-[10px] text-blue-600 mt-1">Note: {r.officer_note}</div>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
