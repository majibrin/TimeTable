import React, { useState, useEffect } from 'react';
import API from '../api/client';
import TimetableGrid from '../components/TimetableGrid';

const TABS = ['TIMETABLE', 'COURSES', 'VENUES', 'REQUESTS'];

export default function OfficerDashboard() {
  const [tab, setTab] = useState('TIMETABLE');
  const [schedules, setSchedules] = useState([]);
  const [courses, setCourses] = useState([]);
  const [venues, setVenues] = useState([]);
  const [lecturers, setLecturers] = useState([]);
  const [cohorts, setCohorts] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [generating, setGenerating] = useState(false);
  const [courseForm, setCourseForm] = useState({ code: '', title: '', unit: 2, cohort: '', lecturer: '' });
  const [venueForm, setVenueForm] = useState({ name: '', capacity: '' });

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [slotsRes, coursesRes, venuesRes, lecturersRes, cohortsRes, requestsRes] = await Promise.all([
        API.get('slots/'),
        API.get('courses/'),
        API.get('venues/'),
        API.get('lecturers/'),
        API.get('cohorts/'),
        API.get('requests/'),
      ]);
      const normalizedSlots = slotsRes.data.map(slot => ({
        course_code: (slot.course_detail || '').split(' - ')[0] || `ID:${slot.course}`,
        room: slot.venue_name || 'TBD',
        lecturer: slot.lecturer_name || 'Unassigned',
        day: (slot.day || 'MON').toUpperCase().substring(0, 3),
        start_time: slot.start_time ? slot.start_time.substring(0, 5) : '08:00',
        duration: parseInt(slot.duration || 1, 10),
      }));
      setSchedules(normalizedSlots);
      setCourses(coursesRes.data);
      setVenues(venuesRes.data);
      setLecturers(lecturersRes.data);
      setCohorts(cohortsRes.data);
      setRequests(requestsRes.data);
    } catch (e) {
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, []);

  const msg = (ok, text) => { if (ok) setSuccess(text); else setError(text); setTimeout(() => { setSuccess(''); setError(''); }, 4000); };

  const handleGenerate = async () => {
    if (!window.confirm('Generate new timetable? Current slots will be replaced.')) return;
    setGenerating(true);
    try {
      const res = await API.post('generate/', { initial_temperature: 1000.0, cooling_rate: 0.95, min_temperature: 0.01 });
      msg(true, `Generated. Conflicts: ${res.data.hard_conflicts}. Sessions: ${res.data.sessions_generated}`);
      await fetchAll();
    } catch (e) {
      msg(false, 'Generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const handlePublish = async () => {
    if (!window.confirm('Publish timetable? It will be visible to all users.')) return;
    try {
      const res = await API.post('publish/');
      msg(true, `Published ${res.data.slots_published} slots`);
    } catch (e) {
      msg(false, 'Publish failed');
    }
  };

  const handleCreateCourse = async (e) => {
    e.preventDefault();
    try {
      await API.post('courses/', {
        code: courseForm.code,
        title: courseForm.title,
        unit: parseInt(courseForm.unit),
        cohort: parseInt(courseForm.cohort),
        lecturer: courseForm.lecturer ? parseInt(courseForm.lecturer) : null,
      });
      msg(true, 'Course created');
      setCourseForm({ code: '', title: '', unit: 2, cohort: '', lecturer: '' });
      fetchAll();
    } catch (e) {
      msg(false, e.response?.data?.code?.[0] || 'Failed to create course');
    }
  };

  const handleDeleteCourse = async (id) => {
    if (!window.confirm('Delete this course?')) return;
    try {
      await API.delete(`courses/${id}/`);
      msg(true, 'Deleted');
      fetchAll();
    } catch (e) {
      msg(false, 'Delete failed');
    }
  };

  const handleCreateVenue = async (e) => {
    e.preventDefault();
    try {
      await API.post('venues/', { name: venueForm.name, capacity: parseInt(venueForm.capacity) });
      msg(true, 'Venue created');
      setVenueForm({ name: '', capacity: '' });
      fetchAll();
    } catch (e) {
      msg(false, e.response?.data?.name?.[0] || 'Failed to create venue');
    }
  };

  const handleDeleteVenue = async (id) => {
    if (!window.confirm('Delete this venue?')) return;
    try {
      await API.delete(`venues/${id}/`);
      msg(true, 'Deleted');
      fetchAll();
    } catch (e) {
      msg(false, 'Delete failed — venue may be in use');
    }
  };

  const handleReview = async (id, decision) => {
    try {
      await API.post(`requests/${id}/review/`, { decision });
      msg(true, `Request ${decision}`);
      fetchAll();
    } catch (e) {
      msg(false, 'Review failed');
    }
  };

  const handleImportCSV = async (e, endpoint) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await API.post(endpoint, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      msg(true, `Imported ${res.data.created_or_updated}. Errors: ${res.data.errors.length}`);
      fetchAll();
    } catch (e) {
      msg(false, 'Import failed');
    }
    e.target.value = '';
  };

  const handleLogout = () => { localStorage.removeItem('token'); window.location.href = '/login'; };

  return (
    <div className="min-h-screen bg-slate-50 font-mono">
      <div className="bg-white border-b border-slate-200 px-4 py-3 flex justify-between items-center">
        <div>
          <h1 className="text-sm font-bold text-slate-900">TIMETABLE OFFICER</h1>
          <p className="text-[10px] text-slate-400">Faculty of Science — GSU</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleGenerate} disabled={generating}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded disabled:opacity-50">
            {generating ? 'GENERATING...' : 'GENERATE'}
          </button>
          <button onClick={handlePublish}
            className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-xs font-bold rounded">
            PUBLISH
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
          loading ? <div className="text-center text-xs text-slate-400 py-12">Loading...</div>
          : <TimetableGrid schedules={schedules} />
        )}

        {tab === 'COURSES' && (
          <div className="max-w-3xl">
            <div className="bg-white border border-slate-200 rounded-lg p-4 mb-4 shadow-sm">
              <h2 className="text-xs font-bold text-slate-700 mb-3 uppercase">Add Course</h2>
              <form onSubmit={handleCreateCourse} className="grid grid-cols-2 gap-3">
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
                <div>
                  <label className="block text-[10px] text-slate-500 mb-1">COHORT</label>
                  <select value={courseForm.cohort} onChange={e => setCourseForm({...courseForm, cohort: e.target.value})} required
                    className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400">
                    <option value="">-- Select --</option>
                    {cohorts.map(c => <option key={c.id} value={c.id}>{c.department_name} {c.level}</option>)}
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="block text-[10px] text-slate-500 mb-1">LECTURER</label>
                  <select value={courseForm.lecturer} onChange={e => setCourseForm({...courseForm, lecturer: e.target.value})}
                    className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400">
                    <option value="">-- Unassigned --</option>
                    {lecturers.map(l => <option key={l.id} value={l.id}>{l.first_name} {l.last_name} ({l.username})</option>)}
                  </select>
                </div>
                <div className="col-span-2">
                  <button type="submit" className="w-full py-2 bg-slate-900 text-white text-xs font-bold rounded hover:bg-slate-700">ADD COURSE</button>
                </div>
              </form>
              <div className="mt-3 pt-3 border-t border-slate-100">
                <label className="block text-[10px] text-slate-500 mb-1">BULK IMPORT CSV (code, title, unit, department, level, lecturer)</label>
                <input type="file" accept=".csv" onChange={e => handleImportCSV(e, 'import/courses/')}
                  className="text-xs text-slate-600" />
              </div>
            </div>
            <div className="bg-white border border-slate-200 rounded-lg shadow-sm">
              <div className="p-3 border-b border-slate-100 text-xs font-bold text-slate-700">COURSES ({courses.length})</div>
              <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
                {courses.map(c => (
                  <div key={c.id} className="flex items-center justify-between p-3">
                    <div>
                      <div className="text-xs font-bold text-slate-800">{c.code}</div>
                      <div className="text-[10px] text-slate-500">{c.title} · {c.unit}u</div>
                    </div>
                    <button onClick={() => handleDeleteCourse(c.id)}
                      className="px-2 py-1 text-[10px] font-bold bg-red-50 text-red-600 border border-red-200 rounded">DEL</button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === 'VENUES' && (
          <div className="max-w-xl">
            <div className="bg-white border border-slate-200 rounded-lg p-4 mb-4 shadow-sm">
              <h2 className="text-xs font-bold text-slate-700 mb-3 uppercase">Add Venue</h2>
              <form onSubmit={handleCreateVenue} className="grid grid-cols-2 gap-3">
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
                  <button type="submit" className="w-full py-2 bg-slate-900 text-white text-xs font-bold rounded hover:bg-slate-700">ADD VENUE</button>
                </div>
              </form>
              <div className="mt-3 pt-3 border-t border-slate-100">
                <label className="block text-[10px] text-slate-500 mb-1">BULK IMPORT CSV (name, capacity)</label>
                <input type="file" accept=".csv" onChange={e => handleImportCSV(e, 'import/venues/')}
                  className="text-xs text-slate-600" />
              </div>
            </div>
            <div className="bg-white border border-slate-200 rounded-lg shadow-sm">
              <div className="p-3 border-b border-slate-100 text-xs font-bold text-slate-700">VENUES ({venues.length})</div>
              <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
                {venues.map(v => (
                  <div key={v.id} className="flex items-center justify-between p-3">
                    <div>
                      <div className="text-xs font-bold text-slate-800">{v.name}</div>
                      <div className="text-[10px] text-slate-500">Capacity: {v.capacity}</div>
                    </div>
                    <button onClick={() => handleDeleteVenue(v.id)}
                      className="px-2 py-1 text-[10px] font-bold bg-red-50 text-red-600 border border-red-200 rounded">DEL</button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === 'REQUESTS' && (
          <div className="max-w-2xl">
            <div className="bg-white border border-slate-200 rounded-lg shadow-sm">
              <div className="p-3 border-b border-slate-100 text-xs font-bold text-slate-700">ADJUSTMENT REQUESTS ({requests.length})</div>
              {requests.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-400">No requests</div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {requests.map(r => (
                    <div key={r.id} className="p-3">
                      <div className="flex justify-between items-start mb-1">
                        <div className="text-xs font-bold text-slate-800">{r.slot_detail}</div>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${r.status === 'PENDING' ? 'bg-amber-50 text-amber-600' : r.status === 'APPROVED' ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'}`}>
                          {r.status}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-500 mb-1">By: {r.lecturer_name}</div>
                      <div className="text-[10px] text-slate-600 mb-2">{r.reason}</div>
                      {r.status === 'PENDING' && (
                        <div className="flex gap-2">
                          <button onClick={() => handleReview(r.id, 'APPROVED')}
                            className="px-3 py-1 text-[10px] font-bold bg-green-50 text-green-600 border border-green-200 rounded">APPROVE</button>
                          <button onClick={() => handleReview(r.id, 'REJECTED')}
                            className="px-3 py-1 text-[10px] font-bold bg-red-50 text-red-600 border border-red-200 rounded">REJECT</button>
                        </div>
                      )}
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
