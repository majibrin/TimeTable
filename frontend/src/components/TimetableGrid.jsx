import React from 'react';

export default function TimetableGrid({ schedules = [] }) {
  const days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
  const timeSlots = [
    '08:00', '09:00', '10:00', '11:00', '12:00',
    '13:00', '14:00', '15:00', '16:00', '17:00'
  ];
  const timeIndex = Object.fromEntries(timeSlots.map((t, i) => [t, i]));
  const numCols = timeSlots.length;

  const getSlotsForDay = (day) => schedules.filter(s => s.day === day);

  const cells = [];

  // Header
  cells.push(
    <div key="hdr-day"
      className="p-1 text-[10px] font-bold text-slate-700 text-center border border-slate-200 bg-slate-100"
      style={{ gridColumn: 1, gridRow: 1 }}>
      DAY
    </div>
  );
  timeSlots.forEach((time, i) => {
    cells.push(
      <div key={`hdr-${time}`}
        className={`p-1 text-[9px] font-bold text-center border border-slate-200 ${time === '13:00' ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-700'}`}
        style={{ gridColumn: i + 2, gridRow: 1 }}>
        {time}
      </div>
    );
  });

  // Day rows
  days.forEach((day, rowIdx) => {
    const gridRow = rowIdx + 2;
    const daySlots = getSlotsForDay(day);

    const byColumn = {};
    for (const s of daySlots) {
      const col = timeIndex[s.start_time?.substring(0, 5)];
      if (col === undefined) continue;
      if (!byColumn[col]) byColumn[col] = [];
      byColumn[col].push(s);
    }

    cells.push(
      <div key={`label-${day}`}
        className="p-1 font-bold text-[10px] text-slate-600 text-center bg-slate-50 border border-slate-200 flex items-center justify-center"
        style={{ gridColumn: 1, gridRow }}>
        {day}
      </div>
    );

    timeSlots.forEach((time, colIdx) => {
      if (time === '13:00') {
        cells.push(
          <div key={`${day}-${time}`}
            className="border border-slate-200 bg-amber-50 flex items-center justify-center"
            style={{ gridColumn: colIdx + 2, gridRow }}>
            <span className="text-[8px] font-bold text-amber-600 [writing-mode:vertical-rl] rotate-180">BREAK</span>
          </div>
        );
        return;
      }

      const matched = byColumn[colIdx] || [];

      if (matched.length === 0) {
        cells.push(
          <div key={`${day}-${time}`}
            className="border border-slate-200 text-center text-slate-200 text-[9px] flex items-center justify-center"
            style={{ gridColumn: colIdx + 2, gridRow }}>
            –
          </div>
        );
        return;
      }

      const maxDuration = Math.max(...matched.map(s => s.duration || 1));

      cells.push(
        <div key={`${day}-${time}`}
          className="border border-slate-200 p-0.5"
          style={{ gridColumn: `${colIdx + 2} / span ${maxDuration}`, gridRow }}>
          <div className="flex flex-col gap-0.5">
            {matched.map((cls, i) => (
              <div key={i} className="bg-blue-50 border-l-2 border-blue-500 px-1 py-0.5 rounded-sm">
                <div className="text-[9px] font-bold text-blue-900 truncate leading-tight">
                  {cls.course_code}
                </div>
                <div className="text-[8px] text-slate-500 truncate leading-tight">
                  {cls.room?.split(' ')[0]}
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    });
  });

  return (
    <div className="font-mono p-3 bg-white rounded-lg border border-slate-200 overflow-x-auto shadow-sm">
      <h3 className="text-sm font-bold text-slate-800 border-b-2 border-slate-900 pb-2 mb-3 tracking-tight">
        TIMETABLE MATRIX
      </h3>
      <div
        className="grid min-w-[900px]"
        style={{
          gridTemplateColumns: `40px repeat(${numCols}, minmax(0, 1fr))`,
          gridTemplateRows: `repeat(${days.length + 1}, auto)`,
        }}
      >
        {cells}
      </div>
    </div>
  );
}
