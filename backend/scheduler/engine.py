import math
import random


class TimetableEngine:
    def __init__(self, initial_temp=1000.0, cooling_rate=0.95, min_temp=0.01, constraint_weights=None):
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp

        # Default weights — overridden by ConstraintSetting from DB
        default = {
            'venue_clash': 1000,
            'cohort_clash': 1000,
            'venue_capacity': 200,
            'faculty_break': 1000,
            'lecture_hours': 1000,
            'same_day_split': 100,
            'saturday_lectures': 50,
            'idle_gaps': 30,
        }
        if constraint_weights:
            default.update(constraint_weights)
        self.w = default

    def run_optimization(self, sessions_data, venues, level_cohorts, total_lecturers):
        venue_ids = [v.id for v in venues]
        venue_caps = {v.id: v.capacity for v in venues}

        # Cache venue department ownership mappings
        venue_depts = {v.id: v.department_id for v in venues}
        cohort_caps = {c.id: c.student_count for c in level_cohorts}

        # Build course level and department constraints metadata registries
        course_levels = {}
        course_depts = {}
        course_offering_depts = {}

        for s in sessions_data:
            c_id = s['course_id']
            course_levels[c_id] = s.get('level', '100L')
            course_depts[c_id] = s.get('course_dept_id', None)
            course_offering_depts[c_id] = s.get('offering_dept_ids', [])

        current_state = self._generate_initial_state(sessions_data, venue_ids)
        current_energy = self.calculate_energy(
            current_state, venue_caps, cohort_caps,
            venue_depts, course_levels, course_depts, course_offering_depts
        )

        best_state = [dict(s) for s in current_state]
        best_energy = current_energy

        temp = self.initial_temp

        while temp > self.min_temp:
            for _ in range(500):
                neighbor_state = self._generate_neighbor(current_state, venue_ids)
                neighbor_energy = self.calculate_energy(
                    neighbor_state, venue_caps, cohort_caps,
                    venue_depts, course_levels, course_depts, course_offering_depts
                )

                delta_e = neighbor_energy - current_energy

                if delta_e < 0 or random.uniform(0.0, 1.0) < math.exp(-delta_e / temp):
                    current_state = neighbor_state
                    current_energy = neighbor_energy

                    if current_energy < best_energy:
                        best_state = [dict(s) for s in current_state]
                        best_energy = current_energy

            temp *= self.cooling_rate

        return best_state, best_energy

    def _generate_initial_state(self, sessions_data, venue_ids):
        state = []
        for s in sessions_data:
            state.append({
                'course_id': s['course_id'],
                'group_kind': s.get('group_kind', 'COHORT'),
                'cohort_ids': s['cohort_ids'],
                'venue_id': random.choice(venue_ids) if venue_ids else None,
                'day_index': random.randint(0, 5),
                'time_slot_index': random.choice([0,1,2,3,4,6,7,8,9]),
                'duration': s['duration']
            })
        return state

    def _generate_neighbor(self, current_state, venue_ids):
        neighbor = [dict(s) for s in current_state]
        idx = random.randint(0, len(neighbor) - 1)
        session = neighbor[idx]

        operation = random.choice(['TIME', 'VENUE'])

        if operation == 'TIME':
            session['day_index'] = random.randint(0, 5)
            valid_slots = [0,1,2,3,4,6,7,8] if session['duration'] == 2 else [0,1,2,3,4,6,7,8,9]
            session['time_slot_index'] = random.choice(valid_slots)
        elif operation == 'VENUE' and venue_ids:
            session['venue_id'] = random.choice(venue_ids)

        return neighbor

    def calculate_energy(self, state, venue_caps, cohort_caps,
                         venue_depts=None, course_levels=None, course_depts=None, course_offering_depts=None):
        w = self.w
        hard_penalty = 0
        soft_penalty = 0

        venue_grid = {}
        cohort_grid = {}
        course_days = {}

        for session in state:
            d = session['day_index']
            t_start = session['time_slot_index']
            dur = session['duration']
            v_id = session['venue_id']
            group_kind = session.get('group_kind', 'COHORT')
            cohort_ids = session['cohort_ids']
            cr_id = session['course_id']

            # GSU Hierarchical Level-Based Venue Constraints Check Logic
            if v_id and venue_depts and course_levels:
                c_level = course_levels.get(cr_id)
                v_dept = venue_depts.get(v_id)
                c_dept = course_depts.get(cr_id)
                c_offerings = course_offering_depts.get(cr_id, [])

                # Rule 1: 100L courses must be in general Faculty-wide venues only (v_dept is None)
                if c_level == '100L' and v_dept is not None:
                    hard_penalty += w['venue_clash']

                # Rule 2: 200L conditional isolation parameters
                elif c_level == '200L':
                    # If multiple separate departments offer it, force into Faculty-wide (v_dept is None)
                    if len(c_offerings) > 1:
                        if v_dept is not None:
                            hard_penalty += w['venue_clash']
                    # If only one department offers it, lock it strictly to that department's room
                    elif len(c_offerings) == 1:
                        target_dept_id = c_offerings[0]
                        if v_dept is not None and v_dept != target_dept_id:
                            hard_penalty += w['venue_clash']

                # Rule 3 & 4: 300L/400L exclusive departmental rooms rule enforcement
                elif c_level in ['300L', '400L']:
                    if v_dept is None or v_dept != c_dept:
                        hard_penalty += w['venue_clash']

            # Venue capacity soft constraint
            if v_id and cohort_ids and group_kind == 'COHORT':
                max_cohort_size = max(cohort_caps.get(c, 0) for c in cohort_ids)
                if max_cohort_size > venue_caps.get(v_id, 0):
                    soft_penalty += w['venue_capacity']

            # Saturday soft penalty
            if d == 5:
                soft_penalty += w['saturday_lectures']

            split_key = (cr_id, group_kind, tuple(sorted(cohort_ids)))
            if split_key not in course_days:
                course_days[split_key] = []
            course_days[split_key].append(d)

            occupied_slots = range(t_start, t_start + dur)

            for t in occupied_slots:
                if t >= 10:
                    hard_penalty += w['lecture_hours']
                    continue

                if t == 5:
                    hard_penalty += w['faculty_break']

                if v_id:
                    v_key = (v_id, d, t)
                    if v_key in venue_grid:
                        hard_penalty += w['venue_clash']
                    venue_grid[v_key] = True

                for c_id in cohort_ids:
                    c_key = (group_kind, c_id, d, t)
                    if c_key in cohort_grid:
                        hard_penalty += w['cohort_clash']
                    cohort_grid[c_key] = True

        for split_key, days in course_days.items():
            if len(days) > 1 and len(set(days)) < len(days):
                soft_penalty += w['same_day_split']

        return hard_penalty + soft_penalty
