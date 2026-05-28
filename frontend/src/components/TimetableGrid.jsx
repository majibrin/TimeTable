import React from 'react';

export default function TimetableGrid({ schedules = [] }) {
  const days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
  const timeSlots = [
    '08:00', '09:00', '10:00', '11:00', '12:00',
    '13:00', '14:00', '15:00', '16:00', '17:00', '18:00'
  ];

  return (
    <div className="font-mono p-4 bg-white rounded-lg border border-slate-200 overflow-x-auto shadow-sm">
      <h3 className="text-lg font-bold text-slate-800 border-b-2 border-slate-900 pb-3 mb-4 tracking-tight">
        OPERATIONAL TIMETABLE MATRIX
      </h3>

      {/* Using an explicit HTML table with fixed layout prevents any shrinking or expanding of populated cells */}
      <table className="w-full min-w-[1000px] border-collapse bg-white table-fixed">
        <thead>
          <tr className="bg-slate-100 border border-slate-200">
            {/* The DAY header column takes up a small fixed width */}
            <th className="w-20 p-3 text-xs font-bold text-slate-700 text-center border-r border-slate-200 tracking-wider">
              DAY
            </th>
            {/* Each hourly header column gets an absolute, uniform portion of the remaining space */}
            {timeSlots.map(time => (
              <th key={time} className="p-3 text-xs font-bold text-slate-700 text-center border-r border-slate-200 last:border-r-0 tracking-wider">
                {time}
              </th>
            ))}
          </tr>
        </thead>
        
        <tbody className="border-x border-b border-slate-200 divide-y divide-slate-200">
          {days.map(day => {
            const daySlots = schedules.filter(s => s.day === day);
            let skipCount = 0;

            return (
              <tr key={day} className="hover:bg-slate-50/30">
                {/* Fixed Day Label column */}
                <td className="w-20 bg-slate-50 p-2 font-bold text-xs text-slate-600 text-center border-r border-slate-200">
                  {day}
                </td>

                {/* Looping through all times for the current day */}
                {timeSlots.map((time, index) => {
                  // If this hour slot was already absorbed by a multi-hour class, skip rendering it
                  if (skipCount > 0) {
                    skipCount--;
                    return null;
                  }

                  // Find if there is a course starting at this specific hour
                  const matchedClass = daySlots.find(s => s.start_time === time);

                  if (matchedClass) {
                    const duration = matchedClass.duration_hours || 1;
                    // Set skipCount so the loop omits the subsequent cells that this block spans across
                    skipCount = duration - 1;

                    return (
                      <td
                        key={time}
                        colSpan={duration}
                        className="p-2 border-r border-slate-200 bg-blue-50/80 border-l-2 border-l-blue-600 align-top"
                      >
                        <div className="flex flex-col justify-between h-[80px]">
                          <div className="space-y-0.5 overflow-hidden">
                            <div className="text-xs font-bold text-blue-900 tracking-tight truncate">
                              {matchedClass.course_code}
                            </div>
                            <div className="text-[10px] font-medium text-slate-700 truncate">
                              {matchedClass.room}
                            </div>
                            <div className="text-[9px] text-slate-500 truncate">
                              {matchedClass.lecturer}
                            </div>
                          </div>
                          <div className="text-[8px] font-bold text-blue-500 self-end tracking-wider">
                            {matchedClass.start_time} ({duration}H)
                          </div>
                        </div>
                      </td>
                    );
                  }

                  // Default empty cell—occupies exactly 1 time slot width track
                  return (
                    <td
                      key={time}
                      className="p-2 border-r border-slate-200 last:border-r-0 text-center text-slate-300 text-xs h-[80px]"
                    >
                      -
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
