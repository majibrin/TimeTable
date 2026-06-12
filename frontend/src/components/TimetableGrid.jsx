import React from 'react';

export default function TimetableGrid({ schedules = [] }) {
  const days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
  const timeSlots = [
    '08:00', '09:00', '10:00', '11:00', '12:00',
    '13:00', '14:00', '15:00', '16:00', '17:00'
  ];

  // Group by day+time — multiple courses can share same slot
  const getSlots = (day, time) =>
    schedules.filter(s => s.day === day && s.start_time === time);

  return (
    <div className="font-mono p-4 bg-white rounded-lg border border-slate-200 overflow-x-auto shadow-sm">
      <h3 className="text-lg font-bold text-slate-800 border-b-2 border-slate-900 pb-3 mb-4 tracking-tight">
        OPERATIONAL TIMETABLE MATRIX
      </h3>

      <table className="w-full min-w-[1000px] border-collapse bg-white table-fixed">
        <thead>
          <tr className="bg-slate-100">
            <th className="w-16 p-2 text-xs font-bold text-slate-700 text-center border border-slate-200">DAY</th>
            {timeSlots.map(time => (
              <th key={time} className={`p-2 text-xs font-bold text-center border border-slate-200 ${time === '13:00' ? 'bg-amber-50 text-amber-700' : 'text-slate-700'}`}>
                {time}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {days.map(day => (
            <tr key={day} className="hover:bg-slate-50/30">
              <td className="bg-slate-50 p-2 font-bold text-xs text-slate-600 text-center border border-slate-200">
                {day}
              </td>

              {timeSlots.map(time => {
                const matched = getSlots(day, time);
                const isBreak = time === '13:00';

                if (isBreak) {
                  return (
                    <td key={time} className="border border-slate-200 bg-amber-50 text-center align-middle p-1">
                      <span className="text-[9px] font-bold text-amber-600 tracking-wider">BREAK</span>
                    </td>
                  );
                }

                if (matched.length === 0) {
                  return (
                    <td key={time} className="border border-slate-200 text-center text-slate-300 text-xs p-2">
                      -
                    </td>
                  );
                }

                return (
                  <td key={time} className="border border-slate-200 p-1 align-top">
                    <div className="flex flex-col gap-1">
                      {matched.map((cls, i) => (
                        <div
                          key={i}
                          className="bg-blue-50 border-l-2 border-blue-600 px-1 py-0.5 rounded-sm"
                        >
                          <div className="text-[10px] font-bold text-blue-900 truncate">{cls.course_code}</div>
                          <div className="text-[9px] text-slate-600 truncate">{cls.room}</div>
                          <div className="text-[8px] text-slate-400 truncate">{cls.lecturer}</div>
                          {cls.duration > 1 && (
                            <div className="text-[8px] text-blue-400 font-bold">{cls.duration}H</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
