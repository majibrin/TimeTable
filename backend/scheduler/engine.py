import math
import random

class TimetableEngine:
    def __init__(self, initial_temp=1000.0, cooling_rate=0.95, min_temp=0.01):
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp

    def run_optimization(self, sessions_data, venues, level_cohorts, total_lecturers):
        """
        Executes the thermodynamic Simulated Annealing optimization cycle.
        """
        venue_ids = [v.id for v in venues]
        venue_caps = {v.id: v.capacity for v in venues}
        cohort_caps = {c.id: c.student_count for c in level_cohorts}

        # Step 1: Initialize random physical starting configuration state
        current_state = self._generate_initial_state(sessions_data, venue_ids)
        current_energy = self.calculate_energy(current_state, venue_caps, cohort_caps)

        best_state = [dict(s) for s in current_state]
        best_energy = current_energy

        temp = self.initial_temp

        # Step 2: Cooling optimization loop
        while temp > self.min_temp:
            # Internal equilibrium iterations per temperature level
            for _ in range(100):
                neighbor_state = self._generate_neighbor(current_state, venue_ids)
                neighbor_energy = self.calculate_energy(neighbor_state, venue_caps, cohort_caps)

                delta_e = neighbor_energy - current_energy

                # Metropolis Acceptance Criterion
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
                'cohort_id': s['cohort_id'],
                'lecturer_id': s['lecturer_id'],
                'venue_id': random.choice(venue_ids) if venue_ids else None,
                'day_index': random.randint(0, 5),        # 0=MON, 5=SAT
                'time_slot_index': random.randint(0, 9),  # 0=08:00, 9=17:00
                'duration': s['duration']
            })
        return state

    def _generate_neighbor(self, current_state, venue_ids):
        """
        Displaces state values while protecting system architecture boundaries.
        """
        neighbor = [dict(s) for s in current_state]
        idx = random.randint(0, len(neighbor) - 1)
        session = neighbor[idx]

        operation = random.choice(['TIME', 'VENUE'])

        if operation == 'TIME':
            session['day_index'] = random.randint(0, 5)
            # Enforce hard upper boundary limit: 2-hour blocks cannot start at index 9 (5 PM)
            max_slot = 9 if session['duration'] == 1 else 8
            session['time_slot_index'] = random.randint(0, max_slot)
        elif operation == 'VENUE' and venue_ids:
            session['venue_id'] = random.choice(venue_ids)

        return neighbor

    def calculate_energy(self, state, venue_caps, cohort_caps):
        """
        H1-H3 Conflict scoring engine utilizing high-speed single-pass hash maps.
        """
        hard_penalty = 0
        soft_penalty = 0

        # Fast lookup allocation indices
        lecturer_grid = {}
        venue_grid = {}
        cohort_grid = {}
        course_days = {} # Tracks days assigned to a course for 3-unit split checks

        for session in state:
            d = session['day_index']
            t_start = session['time_slot_index']
            dur = session['duration']
            v_id = session['venue_id']
            l_id = session['lecturer_id']
            c_id = session['cohort_id']
            cr_id = session['course_id']

            # 1. H1: Venue Capacity Deficit check
            if v_id and c_id:
                if cohort_caps.get(c_id, 0) > venue_caps.get(v_id, 0):
                    hard_penalty += 1000

            # 2. Track days used by each course to optimize 3-unit splits
            if cr_id not in course_days:
                course_days[cr_id] = []
            course_days[cr_id].append(d)

            # Define exact temporal slots taken up by session duration
            occupied_slots = range(t_start, t_start + dur)

            for t in occupied_slots:
                # Operational Window Overflow Cutoff (Past 6:00 PM)
                if t >= 10:
                    hard_penalty += 1000
                    continue

                # Institutional Constraints: Zuhr/Juma'at System Break (13:00 - 14:00 is index 5)
                if t == 5:
                    hard_penalty += 1000

                # H2: Structural Resource Collisions (Lecturers, Venues, Cohorts)
                if l_id:
                    l_key = (l_id, d, t)
                    if l_key in lecturer_grid: hard_penalty += 1000
                    lecturer_grid[l_key] = True

                if v_id:
                    v_key = (v_id, d, t)
                    if v_key in venue_grid: hard_penalty += 1000
                    venue_grid[v_key] = True

                if c_id:
                    c_key = (c_id, d, t)
                    if c_key in cohort_grid: hard_penalty += 1000
                    cohort_grid[c_key] = True

        # 3. Soft Constraint: 3-Unit Courses shouldn't have split components on the same day
        for cr_id, days in course_days.items():
            if len(days) > 1 and days[0] == days[1]:
                soft_penalty += 100  # Discourage, but don't break the system entirely

        return hard_penalty + soft_penalty
