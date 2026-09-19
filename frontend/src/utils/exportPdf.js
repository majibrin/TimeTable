import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

const DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
const TIMES = ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00'];

function formatSessionLabel(session) {
  const courseCode = session.course_code || 'COURSE';
  const room = session.room || 'TBD';
  const title = session.course_title ? `\n${session.course_title}` : '';
  const groupSuffix = session.student_group_detail ? `\n${String(session.student_group_detail).split(' — ').pop()}` : '';
  return `${courseCode}${title}${groupSuffix}\n${room}`;
}

export function exportTimetablePdf(schedules = [], meta = {}) {
  const doc = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' });
  const pageWidth = doc.internal.pageSize.getWidth();
  const dateText = meta.date || '2025/2026';
  const levelText = meta.level || 'ALL LEVELS';
  const sessionText = meta.academicSession || '2025/2026 ACADEMIC SESSION';
  const dayColumnWidth = 52;
  const hourColumnWidth = (pageWidth - 90 - dayColumnWidth) / TIMES.length;

  doc.setFillColor(238, 242, 246);
  doc.rect(26, 18, pageWidth - 52, 32, 'F');
  doc.setFillColor(219, 234, 254);
  doc.rect(26, 50, pageWidth - 52, 28, 'F');
  doc.setFillColor(239, 246, 255);
  doc.rect(26, 78, pageWidth - 52, 28, 'F');

  doc.setTextColor(15, 23, 42);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(14);
  doc.text('GOMBE STATE UNIVERSITY', pageWidth / 2, 35, { align: 'center' });
  doc.setFontSize(13);
  doc.text('FACULTY OF SCIENCE', pageWidth / 2, 65, { align: 'center' });
  doc.setFontSize(10);
  doc.text(sessionText, pageWidth / 2, 94, { align: 'center' });
  doc.setFontSize(10);
  doc.text(`${levelText} ${(meta.semester || 'FIRST').toUpperCase()} SEMESTER LECTURES TIME TABLE — ${dateText}`.toUpperCase(), pageWidth / 2, 110, { align: 'center' });

  const grid = {};
  DAYS.forEach(day => { grid[day] = {}; });
  schedules.forEach(session => {
    const day = (session.day || '').toUpperCase().substring(0, 3);
    const start = (session.start_time || '').slice(0, 5);
    if (!grid[day] || !start) return;
    if (!grid[day][start]) grid[day][start] = [];
    grid[day][start].push(session);
  });

  const head = [['DAY', ...TIMES]];
  const body = DAYS.map(day => {
    const row = [day];
    for (let index = 0; index < TIMES.length; index += 1) {
      const time = TIMES[index];
      if (time === '13:00') {
        row.push({ content: 'BREAK', styles: { fillColor: [255, 237, 160], fontStyle: 'bold', textColor: [0, 0, 0] } });
        continue;
      }
      const matches = grid[day]?.[time] || [];
      if (!matches.length) {
        row.push('');
      } else {
        const duration = Math.max(...matches.map(item => Number(item.duration) || 1), 1);
        const content = matches
          .map(item => formatSessionLabel(item))
          .join('\n');
        row.push({
          content,
          colSpan: Math.min(duration, TIMES.length - index),
          styles: {
            fillColor: [255, 255, 255],
            textColor: [15, 23, 42],
            fontStyle: 'bold',
            halign: 'center',
            valign: 'middle',
            lineColor: [15, 23, 42],
            lineWidth: 0.5,
          },
        });
        index += Math.min(duration, TIMES.length - index) - 1;
      }
    }
    return row;
  });

  autoTable(doc, {
    head,
    body,
    startY: 124,
    margin: { left: 28, right: 28, bottom: 70 },
    tableWidth: pageWidth - 56,
    styles: {
      fontSize: 7,
      cellPadding: 3,
      lineColor: [15, 23, 42],
      lineWidth: 0.4,
      valign: 'middle',
      halign: 'center',
      overflow: 'linebreak',
    },
    headStyles: {
      fillColor: [250, 204, 21],
      textColor: [15, 23, 42],
      fontStyle: 'bold',
      lineColor: [15, 23, 42],
      lineWidth: 0.5,
    },
    columnStyles: {
      0: { cellWidth: dayColumnWidth, fillColor: [191, 219, 254], fontStyle: 'bold' },
      ...Object.fromEntries(TIMES.map((_, index) => [index + 1, { cellWidth: hourColumnWidth }]))
    },
    didParseCell: (data) => {
      if (data.section !== 'body') return;

      if (data.column.index === 0) {
        data.cell.styles.fillColor = [191, 219, 254];
        data.cell.styles.fontStyle = 'bold';
        return;
      }

      const rowShade = data.row.index % 2 === 0 ? [248, 250, 252] : [255, 255, 255];
      data.cell.styles.fillColor = rowShade;
      data.cell.styles.textColor = [15, 23, 42];
      data.cell.styles.lineColor = [15, 23, 42];
      data.cell.styles.lineWidth = 0.4;
    },
    didDrawPage: () => {
      const footerY = doc.internal.pageSize.getHeight() - 42;
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(15, 23, 42);
      doc.setFontSize(8.5);
      doc.text('COMPLAINTS: ALL GENUINE COMPLAINTS SHOULD BE FORWARDED TO THE TIME TABLE OFFICERS VIA +2348022361062/+2348064431262', pageWidth / 2, footerY, { align: 'center' });
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.text('CC: VC, DVCs, Registrar, Deans, Directors, Heads of Department, Faculty of Science (FOS)', pageWidth / 2, footerY + 14, { align: 'center' });
      doc.setFont('helvetica', 'bold');
      doc.text('OFFICER SIGNATURE: ______________________________', pageWidth / 2, footerY + 30, { align: 'center' });
    },
  });

  doc.save(`${meta.filename || 'timetable'}.pdf`);
}
