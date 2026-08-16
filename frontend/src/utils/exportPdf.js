import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

const DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
const TIMES = ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00'];

export function exportTimetablePdf(schedules, meta = {}) {
  const doc = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' });

  doc.setFontSize(14);
  doc.text(meta.title || 'Academic Timetable', 40, 40);
  if (meta.subtitle) {
    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text(meta.subtitle, 40, 58);
    doc.setTextColor(0);
  }

  const grid = {};
  DAYS.forEach(d => { grid[d] = {}; });

  schedules.forEach(s => {
    const day = (s.day || '').toUpperCase().substring(0, 3);
    const time = (s.start_time || '').substring(0, 5);
    if (!grid[day]) return;
    if (!grid[day][time]) grid[day][time] = [];
    grid[day][time].push(s);
  });

  const head = [['DAY', ...TIMES]];
  const body = DAYS.map(day => {
    const row = [day];
    TIMES.forEach(time => {
      if (time === '13:00') {
        row.push('BREAK');
        return;
      }
      const cellSessions = grid[day][time] || [];
      if (cellSessions.length === 0) {
        row.push('');
      } else {
        row.push(
          cellSessions
            .map(s => `${s.course_code}\n${s.room || 'TBD'}`)
            .join('\n---\n')
        );
      }
    });
    return row;
  });

  autoTable(doc, {
    head,
    body,
    startY: meta.subtitle ? 72 : 56,
    styles: { fontSize: 7, cellPadding: 3, valign: 'middle', halign: 'center' },
    headStyles: { fillColor: [30, 41, 59], textColor: 255, fontStyle: 'bold' },
    columnStyles: { 0: { fontStyle: 'bold', fillColor: [241, 245, 249] } },
    didParseCell: (data) => {
      if (data.section === 'body' && data.cell.raw === 'BREAK') {
        data.cell.styles.fillColor = [254, 243, 199];
        data.cell.styles.textColor = [180, 130, 20];
        data.cell.styles.fontStyle = 'bold';
      }
    },
  });

  const filename = (meta.filename || 'timetable') + '.pdf';
  doc.save(filename);
}
