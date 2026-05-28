import React, { useState, useEffect } from 'react';
import TimetableGrid from '../components/TimetableGrid';
import API from '../api/client';

export default function Dashboard() {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchTimetableData = async () => {
      try {
        setLoading(true);
        const res = await API.get('slots/');
        
        // Let's inspect the exact shape of the first slot object from your backend
        if (res.data && res.data.length > 0) {
          const sampleSlot = res.data[0];
          console.log("Raw Backend Slot Object:", sampleSlot);
          
          // If you see the key names here, we can map them perfectly below
          setError(`[DATA INSPECTION] Keys found in slot: ${Object.keys(sampleSlot).join(', ')} | Sample: ${JSON.stringify(sampleSlot)}`);
        }

        const normalizedData = res.data.map(slot => {
          const rawCourse = slot.course_detail || '';
          const courseCode = rawCourse.split(' - ')[0] || `ID: ${slot.course}`;
          const formattedTime = slot.start_time ? slot.start_time.substring(0, 5) : '08:00';

          return {
            course_code: courseCode,
            room: slot.venue_name || 'Unassigned',
            lecturer: slot.lecturer_name || 'Staff',
            day: (slot.day || 'MON').toUpperCase().substring(0, 3),
            start_time: formattedTime,
            duration: parseInt(slot.duration || 1, 10)
          };
        });

        setSchedules(normalizedData);
      } catch (err) {
        setError(`Error: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    fetchTimetableData();
  }, []);

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
        <button onClick={handleLogout} className="px-3 py-1.5 border border-red-200 hover:bg-red-50 text-red-600 rounded font-bold text-xs tracking-wider transition-colors">
          LOGOUT
        </button>
      </div>

      <div className="max-w-6xl mx-auto space-y-6">
        {loading ? (
          <div className="bg-white border border-slate-200 rounded-lg p-12 text-center text-slate-500 text-sm">
            Synchronizing matrix allocations...
          </div>
        ) : error && error.startsWith('[DATA INSPECTION]') ? (
          <div className="space-y-6">
            <div className="bg-blue-50 text-blue-900 p-4 rounded-lg border border-blue-200 text-xs break-all whitespace-pre-wrap">
              {error}
            </div>
            <TimetableGrid schedules={schedules} />
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
