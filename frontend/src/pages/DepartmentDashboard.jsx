import React, { useState, useEffect } from 'react';
import API from '../api/client';
import TimetableGrid from '../components/TimetableGrid';
import { exportTimetablePdf } from '../utils/exportPdf';

const TABS = ['TIMETABLE', 'MY COURSES', 'MY VENUES'];
const STATUS_COLORS = {
  PENDING: 'bg-amber-50 text-amber-600',
  APPROVED: 'bg-green-50 text-green-600',
  REJECTED: 'bg-red-50 text-red-600',
};

export default function DepartmentDashboard() {
  const [tab, setTab] = useState('TIMETABLE');
  const [schedules, setSchedules] = useState([]);
  const [myCourses, setMyCourses] = useState([]);
  const [myVenues, setMyVenues] = useState([]);
  const [cohorts, setCohorts] = useState([]);
  const [departmentId, setDepartmentId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [courseForm, setCourseForm] = useState({ code: '', title: '', unit: 2, selectedCohorts: [] });
  const [venueForm, setVenueForm] = useState({ name: '', capacity: '' });

  const msg = (ok, text) => {
    if (ok) setSuccess(text); else setError(text);
    setTimeout(() => { setSuccess(''); setError(''); }, 4000);
  };

  const fetchAll = async () => {
    setLoading(true);
    try {
      const profileRes = await API.get('');
      const deptId = profileRes.data.department;

      const [slotsRes, coursesRes, venuesRes, cohortsRes] = await Promise.all([
        API.get(`slots/?department=${deptId}`),
        API.get(`courses/?department=${deptId}`),
        API.get(`venues/?department=${deptId}`),
        API.get(`cohorts/?department=${deptId}`),
      ]);

      setDepartmentId(deptId);
      setSchedules(slotsRes.data.map(slot => ({
        course_code: (slot.course_detail || '').split(' - ')[0] || `ID:${slot.course}`,
        room: slot.venue_name || 'TBD',
        day: (slot.day || 'MON').toUpperCase().substring(0, 3),
        start_time: slot.start_time ? slot.start_time.substring(0, 5) : '08:00',
        duration: parseInt(slot.duration || 1, 10),
      })));
      setMyCourses(coursesRes.data);
      setMyVenues(venuesRes.data);
      setCohorts(cohortsRes.data);
    } catch (e) {
      msg(false, 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, []);

  const handleExport = () => {
    exportTimetablePdf(schedules, {
      title: 'Department Timetable',
      subtitle: 'Faculty of Science — GSU',
      filename: 'department-timetable'
    });
  };

  const toggleCohort = (id) => {
    setCourseForm(f => ({
      ...f,
      selectedCohorts: f.selectedCohorts.includes(id)
        ? f.selectedCohorts.filter(c => c !== id)
        : [...f.selectedCohorts, id]
    }));
  };

  const handleSubmitCourse = async (e) => {
    e.preventDefault();
    if (courseForm.selectedCohorts.length === 0) {
      msg(false, 'Select at least one cohort');
      return;
    }
    try {
      await API.post('courses/', {
        code: courseForm.code,
        title: courseForm.title,
        unit: parseInt(courseForm.unit),
        cohorts: courseForm.selectedCohorts,
      });
      msg(true, 'Course submitted for review');
      setCourseForm({ code: '', title: '', unit: 2, selectedCohorts: [] });
      fetchAll();
    } catch (e) {
      msg(false, e.response?.data?.code?.[0] || 'Failed to submit course');
    }
  };

  const handleSubmitVenue = async (e) => {
    e.preventDefault();
    try {
      await API.post('venues/', { name: venueForm.name, capacity: parseInt(venueForm.capacity) });
      msg(true, 'Venue submitted for review');
      setVenueForm({ name: '', capacity: '' });
      fetchAll();
    } catch (e) {
      msg(false, e.response?.data?.name?.[0] || 'Failed to submit venue');
    }
  };

  const handleLogout = () => { localStorage.removeItem('token'); window.location.href = '/login'; };

  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      <div className="bg-white border-b border-slate-200 px-4 py-3 flex justify-between items-center">
        <div>
          <h1 className="text-sm font-bold text-slate-900">DEPARTMENT</h1>
          <p className="text-[10px] text-slate-400">Course & Venue Submission — GSU</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleExport}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold rounded">
            EXPORT PDF
          </button>
          <button onClick={handleLogout}
            className="px-3 py-1.5 border border-red-200 text-red-600 text-xs font-bold rounded">
            LOGOUT
          </button>
        </div>
      </div>

      <div className="flex border-b border-slate-200 bg-white px-4">
        {TABS.map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-[11px] font-bold border-b-2 transition-colors ${tab === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-600'}`}>
            {t}
          </button>
        ))}
      </div>

      <div className="p-4">
        {error && <div className="bg-red-50 text-red-700 text-xs p-3 rounded mb-3 border border-red-200">{error}</div>}
        {success && <div className="bg-green-50 text-green-700 text-xs p-3 rounded mb-3 border border-green-200">{success}</div>}

        {tab === 'TIMETABLE' && (
          loading
            ? <div className="text-center text-xs text-slate-400 py-12">Loading...</div>
            : schedules.length === 0
              ? <div className="text-center text-xs text-slate-400 py-12">No sessions scheduled yet</div>
              : <TimetableGrid schedules={schedules} />
        )}

        {tab === 'MY COURSES' && (
          <div className="max-w-3xl">
            <div className="bg-white border border-slate-200 rounded-lg p-4 mb-4 shadow-sm">
              <h2 className="text-xs font-bold text-slate-700 mb-3 uppercase">Submit Course</h2>
              <form onSubmit={handleSubmitCourse} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] text-slate-500 mb-1">CODE</label>
                    <input value={courseForm.code} onChange={e => setCourseForm({...courseForm, code: e.target.value})} required
                      className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400" />
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-500 mb-1">TITLE</label>
                    <input value={courseForm.title} onChange={e => setCourseForm({...courseForm, title: e.target.value})} required
                      className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400" />
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-500 mb-1">UNITS</label>
                    <select value={courseForm.unit} onChange={e => setCourseForm({...courseForm, unit: e.target.value})}
                      className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400">
                      {[1,2,3].map(u => <option key={u} value={u}>{u}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500 mb-2">
                    COHORTS ({courseForm.selectedCohorts.length} selected)
                  </label>
                  <div className="border border-slate-200 rounded p-2 max-h-40 overflow-y-auto grid grid-cols-2 gap-1">
                    {cohorts.map(c => (
                      <label key={c.id} className="flex items-center gap-1.5 cursor-pointer hover:bg-slate-50 p-1 rounded">
                        <input type="checkbox" checked={courseForm.selectedCohorts.includes(c.id)}
                          onChange={() => toggleCohort(c.id)} className="w-3 h-3" />
                        <span className="text-[10px] text-slate-700">{c.level}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <button type="submit" className="w-full py-2 bg-slate-900 text-white text-xs font-bold rounded hover:bg-slate-700">
                  SUBMIT FOR REVIEW
                </button>
              </form>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg shadow-sm">
              <div className="p-3 border-b border-slate-100 text-xs font-bold text-slate-700">MY COURSES ({myCourses.length})</div>
              <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
                {myCourses.map(c => (
                  <div key={c.id} className="p-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="text-xs font-bold text-slate-800">{c.code}</div>
                        <div className="text-[10px] text-slate-500">{c.title} · {c.unit}u</div>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${STATUS_COLORS[c.status] || ''}`}>
                        {c.status}
                      </span>
                    </div>
                    {c.status === 'REJECTED' && c.officer_note && (
                      <div className="text-[10px] text-red-600 mt-1">Note: {c.officer_note}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === 'MY VENUES' && (
          <div className="max-w-xl">
            <div className="bg-white border border-slate-200 rounded-lg p-4 mb-4 shadow-sm">
              <h2 className="text-xs font-bold text-slate-700 mb-3 uppercase">Submit Venue</h2>
              <form onSubmit={handleSubmitVenue} className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] text-slate-500 mb-1">NAME</label>
                  <input value={venueForm.name} onChange={e => setVenueForm({...venueForm, name: e.target.value})} required
                    className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400" />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500 mb-1">CAPACITY</label>
                  <input type="number" value={venueForm.capacity} onChange={e => setVenueForm({...venueForm, capacity: e.target.value})} required
                    className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400" />
                </div>
                <div className="col-span-2">
                  <button type="submit" className="w-full py-2 bg-slate-900 text-white text-xs font-bold rounded hover:bg-slate-700">SUBMIT FOR REVIEW</button>
                </div>
              </form>
            </div>
            <div className="bg-white border border-slate-200 rounded-lg shadow-sm">
              <div className="p-3 border-b border-slate-100 text-xs font-bold text-slate-700">MY VENUES ({myVenues.length})</div>
              <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
                {myVenues.map(v => (
                  <div key={v.id} className="p-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="text-xs font-bold text-slate-800">{v.name}</div>
                        <div className="text-[10px] text-slate-500">Capacity: {v.capacity}</div>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${STATUS_COLORS[v.status] || ''}`}>
                        {v.status}
                      </span>
                    </div>
                    {v.status === 'REJECTED' && v.officer_note && (
                      <div className="text-[10px] text-red-600 mt-1">Note: {v.officer_note}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
