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
const LEVELS = ['100L', '200L', '300L', '400L'];

function slotLevel(slot) {
  return (slot.student_group_detail || slot.cohort_detail || '').match(/\b\d{3}L\b/)?.[0] || '';
}

export default function DepartmentDashboard() {
  const [tab, setTab] = useState('TIMETABLE');
  const [schedules, setSchedules] = useState([]);
  const [myCourses, setMyCourses] = useState([]);
  const [myVenues, setMyVenues] = useState([]);
  const [cohorts, setCohorts] = useState([]);
  const [departmentId, setDepartmentId] = useState(null);
  const [selectedLevel, setSelectedLevel] = useState('ALL');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [courseForm, setCourseForm] = useState({ 
    code: '', 
    title: '', 
    unit: 2, 
    selectedCohorts: [],
    hasPractical: false 
  });
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

      const slotResponses = await Promise.all([
        ...LEVELS.map(level => API.get(`slots/?student_department=${deptId}&level=${level}`)),
      ]);
      const [coursesRes, venuesRes, cohortsRes] = await Promise.all([
        API.get(`courses/?department=${deptId}`),
        API.get(`venues/?department=${deptId}`),
        API.get(`cohorts/?department=${deptId}`),
      ]);

      setDepartmentId(deptId);
      setSchedules(slotResponses.flatMap(response => response.data).map(slot => ({
        course_code: (slot.course_detail || '').split(' - ')[0] || `ID:${slot.course}`,
        room: slot.venue_name || 'TBD',
        student_group_detail: slot.student_group_detail,
        level: slotLevel(slot),
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
    const exportSlice = selectedLevel === 'ALL' ? schedules : schedules.filter(slot => slot.level === selectedLevel);
    exportTimetablePdf(exportSlice, {
      level: selectedLevel === 'ALL' ? 'ALL LEVELS' : selectedLevel,
      semester: 'FIRST',
      title: `${selectedLevel === 'ALL' ? 'ALL LEVELS' : selectedLevel} FIRST SEMESTER LECTURES TIME TABLE`,
      subtitle: `${selectedLevel === 'ALL' ? 'All Levels' : selectedLevel} — Faculty of Science, GSU`,
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
        code: courseForm.code.trim().toUpperCase(),
        title: courseForm.title.trim(),
        unit: parseInt(courseForm.unit),
        department: departmentId, 
        cohorts: courseForm.selectedCohorts,
        has_practical: courseForm.hasPractical, 
      });
      msg(true, 'Course submitted for review');
      setCourseForm({ code: '', title: '', unit: 2, selectedCohorts: [], hasPractical: false });
      fetchAll();
    } catch (e) {
      msg(false, e.response?.data?.code?.[0] || 'Failed to submit course');
    }
  };

  const handleSubmitVenue = async (e) => {
    e.preventDefault();
    try {
      await API.post('venues/', { name: venueForm.name.trim(), capacity: parseInt(venueForm.capacity) });
      msg(true, 'Venue submitted for review');
      setVenueForm({ name: '', capacity: '' });
      fetchAll();
    } catch (e) {
      msg(false, e.response?.data?.name?.[0] || 'Failed to submit venue');
    }
  };

  const handleLogout = () => { localStorage.removeItem('token'); window.location.href = '/login'; };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200/60 px-4 py-3">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="text-sm font-bold text-slate-900">DEPARTMENT PANEL</h1>
            <p className="text-[10px] sm:text-xs text-slate-400">Course & Venue Submission — GSU</p>
          </div>
          <div className="flex gap-2">
            <button onClick={handleExport}
              className="px-3 py-1.5 text-[10px] sm:text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors shadow-sm">
              EXPORT PDF
            </button>
            <button onClick={handleLogout}
              className="px-3 py-1.5 text-[10px] sm:text-xs font-bold border border-red-300 hover:bg-red-50 text-red-600 rounded transition-colors">
              LOGOUT
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200/60 bg-white px-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-nowrap items-center gap-1 overflow-x-auto">
            {TABS.map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`px-4 py-2.5 text-[10px] sm:text-xs font-bold border-b-2 whitespace-nowrap transition-colors ${
                  tab === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-600'
                }`}>
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 md:py-6">
        {error && <div className="bg-red-50 text-red-700 text-xs p-3 rounded-xl mb-4 border border-red-200">{error}</div>}
        {success && <div className="bg-green-50 text-green-700 text-xs p-3 rounded-xl mb-4 border border-green-200">{success}</div>}

        {tab === 'TIMETABLE' && (
          loading
            ? <div className="text-center text-xs text-slate-400 py-12">Loading...</div>
            : schedules.length === 0
              ? <div className="text-center text-xs text-slate-400 py-12 bg-white rounded-2xl border border-slate-200/60 p-8">No sessions scheduled yet</div>
              : <>
                <div className="flex flex-wrap gap-2 mb-4">
                  {['ALL', ...LEVELS].map(level => (
                    <button key={level} onClick={() => setSelectedLevel(level)}
                      className={`px-4 py-2 text-[10px] font-bold rounded-lg border ${selectedLevel === level ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-600 border-slate-200'}`}>
                      {level === 'ALL' ? 'ALL' : level}
                    </button>
                  ))}
                </div>
                <div className="bg-white rounded-2xl border border-slate-200/60 p-4 shadow-sm"><TimetableGrid schedules={selectedLevel === 'ALL' ? schedules : schedules.filter(slot => slot.level === selectedLevel)} /></div>
              </>
        )}

        {tab === 'MY COURSES' && (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            {/* Form Column - Left */}
            <div className="lg:col-span-2">
              <div className="bg-white border border-slate-200/60 rounded-2xl p-5 shadow-sm sticky top-[200px]">
                <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-4">Submit Course</h2>
                <form onSubmit={handleSubmitCourse} className="space-y-3">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1">Code</label>
                    <input value={courseForm.code} onChange={e => setCourseForm({...courseForm, code: e.target.value})} required
                      className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-blue-600/20 focus:border-blue-600 bg-slate-50/50 font-medium" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1">Title</label>
                    <input value={courseForm.title} onChange={e => setCourseForm({...courseForm, title: e.target.value})} required
                      className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-blue-600/20 focus:border-blue-600 bg-slate-50/50 font-medium" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1">Units</label>
                    <select value={courseForm.unit} onChange={e => setCourseForm({...courseForm, unit: e.target.value})}
                      className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-blue-600/20 focus:border-blue-600 bg-slate-50/50 font-bold">
                      {[1,2,3].map(u => <option key={u} value={u}>{u}</option>)}
                    </select>
                  </div>

                  <div className="flex items-center py-1">
                    <label className="flex items-center gap-1.5 cursor-pointer">
                      <input type="checkbox" checked={courseForm.hasPractical}
                        onChange={e => setCourseForm({...courseForm, hasPractical: e.target.checked})}
                        className="w-3.5 h-3.5 rounded border-slate-300 text-blue-600 focus:ring-blue-600" />
                      <span className="text-[10px] font-bold text-slate-600">Requires lab/practical sessions</span>
                    </label>
                  </div>

                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-2">
                      Target Cohorts ({courseForm.selectedCohorts.length} selected)
                    </label>
                    <div className="border border-slate-200 rounded-xl p-2 max-h-40 overflow-y-auto grid grid-cols-1 gap-1 bg-slate-50/30">
                      {cohorts.map(c => (
                        <label key={c.id} className="flex items-center gap-1.5 cursor-pointer hover:bg-slate-50 p-1.5 rounded-lg transition-colors">
                          <input type="checkbox" checked={courseForm.selectedCohorts.includes(c.id)}
                            onChange={() => toggleCohort(c.id)} className="w-3.5 h-3.5 rounded border-slate-300 text-blue-600 focus:ring-blue-600" />
                          <span className="text-[10px] font-medium text-slate-700">{c.level} ({c.student_count} students)</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <button type="submit" className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-black rounded-xl transition-colors shadow-sm">
                    SUBMIT FOR REVIEW
                  </button>
                </form>
              </div>
            </div>

            {/* List Column - Right */}
            <div className="lg:col-span-3">
              <div className="bg-white border border-slate-200/60 rounded-2xl shadow-sm">
                <div className="p-4 border-b border-slate-100 text-xs font-bold text-slate-700">MY SUBMITTED COURSES ({myCourses.length})</div>
                {myCourses.length === 0 ? (
                  <div className="p-8 text-center text-xs text-slate-400">No courses submitted yet</div>
                ) : (
                  <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
                    {myCourses.map(c => (
                      <div key={c.id} className="p-4 hover:bg-slate-50/50 transition-colors">
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="text-xs font-bold text-slate-800">{c.code}</div>
                            <div className="text-[10px] text-slate-500">{c.title} · {c.unit}u {c.has_practical ? '· Practical' : ''}</div>
                          </div>
                          <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${STATUS_COLORS[c.status] || ''}`}>
                            {c.status}
                          </span>
                        </div>
                        {c.status === 'REJECTED' && c.officer_note && (
                          <div className="text-[10px] text-red-600 mt-1.5 font-medium bg-red-50 p-1.5 rounded-lg border border-red-100">
                            Rejection Reason: {c.officer_note}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {tab === 'MY VENUES' && (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            {/* Form Column - Left */}
            <div className="lg:col-span-2">
              <div className="bg-white border border-slate-200/60 rounded-2xl p-5 shadow-sm sticky top-[200px]">
                <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-4">Submit Venue</h2>
                <form onSubmit={handleSubmitVenue} className="space-y-3">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1">Name</label>
                    <input value={venueForm.name} onChange={e => setVenueForm({...venueForm, name: e.target.value})} required
                      placeholder="e.g. DEPT LAB 1"
                      className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-blue-600/20 focus:border-blue-600 bg-slate-50/50 font-medium" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1">Capacity</label>
                    <input type="number" value={venueForm.capacity} onChange={e => setVenueForm({...venueForm, capacity: e.target.value})} required
                      placeholder="e.g. 50"
                      className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-blue-600/20 focus:border-blue-600 bg-slate-50/50 font-medium" />
                  </div>
                  <button type="submit" className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-black rounded-xl transition-colors shadow-sm">
                    SUBMIT FOR REVIEW
                  </button>
                </form>
              </div>
            </div>

            {/* List Column - Right */}
            <div className="lg:col-span-3">
              <div className="bg-white border border-slate-200/60 rounded-2xl shadow-sm">
                <div className="p-4 border-b border-slate-100 text-xs font-bold text-slate-700">MY SUBMITTED VENUES ({myVenues.length})</div>
                {myVenues.length === 0 ? (
                  <div className="p-8 text-center text-xs text-slate-400">No venues submitted yet</div>
                ) : (
                  <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
                    {myVenues.map(v => (
                      <div key={v.id} className="p-4 hover:bg-slate-50/50 transition-colors">
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="text-xs font-bold text-slate-800">{v.name}</div>
                            <div className="text-[10px] text-slate-500">Capacity: {v.capacity}</div>
                          </div>
                          <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${STATUS_COLORS[v.status] || ''}`}>
                            {v.status}
                          </span>
                        </div>
                        {v.status === 'REJECTED' && v.officer_note && (
                          <div className="text-[10px] text-red-600 mt-1.5 font-medium bg-red-50 p-1.5 rounded-lg border border-red-100">
                            Rejection Reason: {v.officer_note}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}