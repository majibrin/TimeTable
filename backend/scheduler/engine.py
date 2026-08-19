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
            'venue_capacity': 1000,
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
        cohort_caps = {c.id: c.student_count for c in level_cohorts}

        current_state = self._generate_initial_state(sessions_data, venue_ids)
        current_energy = self.calculate_energy(current_state, venue_caps, cohort_caps)

        best_state = [dict(s) for s in current_state]
        best_energy = current_energy

        temp = self.initial_temp

        while temp > self.min_temp:
            for _ in range(500):
                neighbor_state = self._generate_neighbor(current_state, venue_ids)
                neighbor_energy = self.calculate_energy(neighbor_state, venue_caps, cohort_caps)

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
                'group_kind': s.get('group_kind', 'COHORT'),  # 'COHORT' or 'GROUP'
                'cohort_ids': s['cohort_ids'],   # list of clash-unit IDs (LevelCohort or StudentGroup)
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

    def calculate_energy(self, state, venue_caps, cohort_caps):
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
            cohort_ids = session['cohort_ids']  # list
            cr_id = session['course_id']

            # Venue capacity — use largest clash-unit size (only meaningful for
            # COHORT-based sessions today; GROUP-based sessions have no known
            # size yet, so this check is skipped for them rather than guessed).
            if v_id and cohort_ids and group_kind == 'COHORT':
                max_cohort_size = max(cohort_caps.get(c, 0) for c in cohort_ids)
                if max_cohort_size > venue_caps.get(v_id, 0):
                    hard_penalty += w['venue_capacity']

            # Saturday soft penalty
            if d == 5:
                soft_penalty += w['saturday_lectures']

            # Track days for split course soft constraint
            if cr_id not in course_days:
                course_days[cr_id] = []
            course_days[cr_id].append(d)

            occupied_slots = range(t_start, t_start + dur)

            for t in occupied_slots:
                # Lecture hours hard constraint
                if t >= 10:
                    hard_penalty += w['lecture_hours']
                    continue

                # Faculty break hard constraint (index 5 = 13:00)
                if t == 5:
                    hard_penalty += w['faculty_break']

                # Venue clash
                if v_id:
                    v_key = (v_id, d, t)
                    if v_key in venue_grid:
                        hard_penalty += w['venue_clash']
                    venue_grid[v_key] = True

                # Cohort/group clash — namespaced by group_kind so a
                # StudentGroup id and a LevelCohort id never collide.
                for c_id in cohort_ids:
                    c_key = (group_kind, c_id, d, t)
                    if c_key in cohort_grid:
                        hard_penalty += w['cohort_clash']
                    cohort_grid[c_key] = True

        # Same day split soft constraint
        for cr_id, days in course_days.items():
            if len(days) > 1 and days[0] == days[1]:
                soft_penalty += w['same_day_split']

        return hard_penalty + soft_penalty
