# Iron Temple -- Bodybuilding & Athletic Performance Plan

> Evidence-based 12-week hypertrophy program with Indian-American hybrid nutrition.
> Intermediate lifter | 4 days/week | 75 min max | Lean aesthetic focus.

---

## Phase 1: Requirements

### 1.1 Problem Statement

**What:** An intermediate lifter (1-3 years training) needs a structured, periodized program that builds lean muscle with athletic performance, combined with a practical diet plan for an Indian living in Seattle.

**Who:** Intermediate trainee, full commercial gym access, 4 days/week max, 75 min/session max.

**Cost of inaction:** Plateau at intermediate level, junk volume, imbalanced physique, poor nutrition-to-training alignment, spinning wheels.

**Why now:** The intermediate stage is where most lifters stall without periodized programming and intentional nutrition.

### 1.2 User Stories

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| US-1 | As a lifter, I want a 4-day Upper/Lower split hitting each muscle 2x/week | GIVEN the split WHEN I follow it for a week THEN every major muscle has been trained twice |
| US-2 | As an intermediate, I want progressive overload built in with double progression | GIVEN Week N weights WHEN I hit the top of the rep range for all sets THEN I increase load by 5-10 lbs |
| US-3 | As someone focused on lean aesthetics, I want targeted volume for delts, back width, arms | GIVEN aesthetic priority muscles WHEN I count weekly sets THEN delts get 16-22 sets, back 14-22, arms 14-20 |
| US-4 | As an Indian in Seattle, I want a hybrid diet with Indian meals + US grocery availability | GIVEN meal plan WHEN I shop at Indian store + Costco THEN I can hit 180-200g protein daily |
| US-5 | As a busy person, I want sessions under 75 minutes | GIVEN superset-based programming WHEN I time a session THEN it completes in 60-75 minutes |
| US-6 | As someone wanting athleticism, I want explosive work integrated | GIVEN each session WHEN I start THEN 2-3 sets of power/explosive work precede hypertrophy volume |
| US-7 | As a visual learner, I want pictographic exercise guides with form cues | GIVEN any exercise in the plan WHEN I look at the guide THEN I see illustration + 3 form cues + common mistakes |

### 1.3 Scope Boundaries

**In scope:**
- 12-week periodized training program (3 mesocycles)
- Complete exercise guide with form cues, EMG-based exercise selection, common mistakes
- Indian-American hybrid meal plans with macros per meal
- Grocery lists (Indian store + US grocery)
- Progressive overload tracking system
- Pre/post workout nutrition protocol

**Out of scope:**
- Supplementation protocol (beyond whey protein)
- Competition prep / peaking
- Injury rehab programming
- Cardio programming (mention briefly, not program)
- Mobile app development (future phase)

### 1.4 Non-Functional Requirements

- Session duration: <= 75 minutes including warm-up
- Recovery: manageable on moderate surplus (+200-300 kcal)
- Adaptability: alternate exercises listed for every movement
- Diet: practical for Seattle grocery availability
- Visual: printable PDF-quality exercise cards

---

## Phase 2: Design

### 2.1 Training Architecture

#### Split: Upper/Lower, 4 Days/Week

```
Monday:    Upper A (Horizontal Push/Pull emphasis)
Tuesday:   Lower A (Quad emphasis)
Wednesday: REST
Thursday:  Upper B (Vertical Push/Pull emphasis)
Friday:    Lower B (Hip hinge/Hamstring emphasis)
Saturday:  REST (or active recovery / light cardio)
Sunday:    REST
```

**Frequency per muscle:** 2x/week (research-validated optimal for intermediates)

#### Volume Landmarks (Sets/Week)

| Muscle Group | MEV (Start) | MAV (Peak) | MRV (Never exceed) | Our Target Range |
|---|---|---|---|---|
| Chest | 10 | 12-20 | 22 | 10-18 across mesocycle |
| Back (Width + Thickness) | 10 | 14-22 | 25 | 10-20 |
| Side Delts | 10 | 16-22 | 26 | 12-20 |
| Rear Delts | 8 | 12-18 | 22 | 8-16 |
| Front Delts | 6 | 6-8 | 12 | 6-8 (covered by pressing) |
| Quads | 8 | 12-18 | 20 | 8-16 |
| Hamstrings | 6 | 10-16 | 20 | 8-14 |
| Biceps | 8 | 14-20 | 26 | 10-18 |
| Triceps | 6 | 10-14 | 18 | 8-14 |
| Calves | 8 | 12-16 | 20 | 8-14 |
| Glutes | 6 | 10-16 | 20 | 8-14 (covered by compounds) |

#### Progressive Overload: Double Progression + RIR

**Method:** Pick a rep range (e.g., 8-12). Work at a given weight until you hit the top of the range for ALL prescribed sets. Then increase weight and reset to the bottom of the range.

**RIR targets across mesocycle:**
- Week 1: 3-4 RIR (further from failure)
- Week 2: 2-3 RIR
- Week 3: 1-2 RIR
- Week 4: DELOAD (50% volume, 5+ RIR)

**Load increases:**
- Compounds (squat, bench, row, RDL): +5-10 lbs when top of range reached
- Isolation (curls, laterals, extensions): +2.5-5 lbs when top of range reached

#### 12-Week Periodization

```
MACROCYCLE: 12 Weeks

Mesocycle 1 (Weeks 1-4): BASE VOLUME
  Week 1: MEV (~10 sets/large, ~8 sets/small), 3-4 RIR
  Week 2: +1-2 sets/group, 2-3 RIR
  Week 3: +1-2 sets/group, 1-2 RIR
  Week 4: DELOAD -- 50% volume, same loads, 5+ RIR

Mesocycle 2 (Weeks 5-8): VOLUME PUSH
  Week 5: Restart at Meso 1 Week 2 volume, 3 RIR
  Week 6: +1-2 sets, 2-3 RIR
  Week 7: +1-2 sets, approaching MAV, 1-2 RIR
  Week 8: DELOAD

Mesocycle 3 (Weeks 9-12): PEAK INTENSITY
  Week 9: Restart at Meso 2 Week 6 volume, 2-3 RIR
  Week 10: +1-2 sets, 2 RIR
  Week 11: Approach MRV for priority muscles, 0-1 RIR
  Week 12: DELOAD + Test new maxes
```

#### Rest Periods

| Exercise Type | Rest | Rationale |
|---|---|---|
| Heavy compounds (squat, bench, RDL) | 2-3 min | Maintain load across sets |
| Secondary compounds (incline press, rows, lunges) | 90-120 sec | Balance recovery and density |
| Isolation exercises | 60-90 sec | Full local recovery not needed |
| Supersets (antagonist pairs) | 60s between exercises, 90s between rounds | 30-40% time savings, no hypertrophy penalty |

#### Rep Ranges

| Exercise Category | Rep Range | RIR | Rationale |
|---|---|---|---|
| Main compounds (squat, bench, row, RDL) | 6-10 | 2-3 | Mechanical tension focus |
| Secondary compounds (incline press, lunges, pulldowns) | 8-12 | 1-2 | Hypertrophy sweet spot |
| Isolation (curls, laterals, extensions) | 10-15 | 0-1 | Metabolic stress + safe near failure |
| Myo-rep finishers | 12-15 activation + 3-5 mini-sets | 0-1 | Time-efficient volume |

---

### 2.2 The Workouts

#### UPPER A -- Horizontal Push/Pull (Monday)

| # | Exercise | Sets x Reps | RIR | Rest | Superset |
|---|----------|-------------|-----|------|----------|
| A0 | Med Ball Chest Pass (explosive) | 3x5 | N/A | 90s | -- |
| A1 | Barbell Bench Press | 4x6-10 | 2-3 | 60s | SS with A2 |
| A2 | Barbell Bent-Over Row | 4x6-10 | 2-3 | 90s | SS with A1 |
| B1 | Incline Dumbbell Press (30 deg) | 3x8-12 | 1-2 | 60s | SS with B2 |
| B2 | Seated Cable Row | 3x8-12 | 1-2 | 90s | SS with B1 |
| C1 | Dumbbell Lateral Raise | 3x12-15 | 0-1 | 60s | SS with C2 |
| C2 | Face Pulls | 3x12-15 | 0-1 | 60s | SS with C1 |
| D1 | Barbell Curl | 2x8-12 + 1 myo-rep set | 0-1 | 60s | SS with D2 |
| D2 | Tricep Pushdown (rope) | 2x10-12 + 1 myo-rep set | 0-1 | 60s | SS with D1 |

**Volume tally:** Chest 7, Back 7, Side Delts 3, Rear Delts 3, Biceps 3, Triceps 3
**Estimated time:** ~62 minutes

#### LOWER A -- Quad Emphasis (Tuesday)

| # | Exercise | Sets x Reps | RIR | Rest | Superset |
|---|----------|-------------|-----|------|----------|
| A0 | Box Jumps (explosive) | 3x5 | N/A | 90s | -- |
| A1 | Barbell Back Squat | 4x6-10 | 2-3 | 2.5 min | -- |
| B1 | Leg Press | 3x8-12 | 1-2 | 90s | -- |
| C1 | Walking Lunges (DB) | 3x10-12/leg | 1-2 | 90s | -- |
| D1 | Leg Curl (lying/seated) | 3x10-12 | 1-2 | 60s | SS with D2 |
| D2 | Leg Extension | 3x10-12 | 1-2 | 60s | SS with D1 |
| E1 | Standing Calf Raise | 3x10-15 + 1 myo-rep | 0-1 | 60s | -- |
| F1 | Hanging Leg Raise (abs) | 3x10-15 | 1-2 | 60s | -- |

**Volume tally:** Quads 10 (squat+leg press+lunge+ext), Hams 3, Calves 4, Glutes 7 (squat+lunge+leg press)
**Estimated time:** ~68 minutes

#### UPPER B -- Vertical Push/Pull (Thursday)

| # | Exercise | Sets x Reps | RIR | Rest | Superset |
|---|----------|-------------|-----|------|----------|
| A0 | Explosive Push-ups (clap) | 3x5 | N/A | 90s | -- |
| A1 | Overhead Press (barbell) | 4x6-10 | 2-3 | 60s | SS with A2 |
| A2 | Pull-ups (weighted if possible) | 4x6-10 | 2-3 | 90s | SS with A1 |
| B1 | Cable Fly (low-to-high) | 3x10-12 | 1-2 | 60s | SS with B2 |
| B2 | Lat Pulldown (wide grip) | 3x8-12 | 1-2 | 90s | SS with B1 |
| C1 | Cable Lateral Raise | 3x12-15 | 0-1 | 60s | SS with C2 |
| C2 | Rear Delt Fly (incline bench) | 3x12-15 | 0-1 | 60s | SS with C1 |
| D1 | Incline Dumbbell Curl | 2x8-12 + 1 myo-rep | 0-1 | 60s | SS with D2 |
| D2 | Overhead Tricep Extension (cable) | 2x10-12 + 1 myo-rep | 0-1 | 60s | SS with D1 |

**Volume tally:** Chest 3 (fly) + OHP front delt, Back 7, Side Delts 3, Rear Delts 3, Biceps 3, Triceps 3
**Estimated time:** ~63 minutes

#### LOWER B -- Hip Hinge/Hamstring (Friday)

| # | Exercise | Sets x Reps | RIR | Rest | Superset |
|---|----------|-------------|-----|------|----------|
| A0 | Broad Jumps (explosive) | 3x5 | N/A | 90s | -- |
| A1 | Romanian Deadlift | 4x6-10 | 2-3 | 2.5 min | -- |
| B1 | Bulgarian Split Squat (DB) | 3x8-12/leg | 1-2 | 90s | -- |
| C1 | Seated Leg Curl | 3x10-12 | 1-2 | 60s | SS with C2 |
| C2 | Leg Extension | 3x10-12 | 1-2 | 60s | SS with C1 |
| D1 | Hip Thrust (barbell) | 3x8-12 | 1-2 | 90s | -- |
| E1 | Seated Calf Raise | 3x10-15 + 1 myo-rep | 0-1 | 60s | -- |
| F1 | Cable Crunch (abs) | 3x12-15 | 1-2 | 60s | -- |

**Volume tally:** Hams 7 (RDL+leg curl), Quads 6 (split squat+ext), Glutes 7 (RDL+split squat+hip thrust), Calves 4
**Estimated time:** ~70 minutes

#### Weekly Volume Summary

| Muscle | Upper A | Lower A | Upper B | Lower B | WEEKLY TOTAL |
|--------|---------|---------|---------|---------|-------------|
| Chest | 7 | -- | 3 | -- | **10** |
| Back | 7 | -- | 7 | -- | **14** |
| Side Delts | 3 | -- | 3 | -- | **6** + pressing indirect = ~10 |
| Rear Delts | 3 | -- | 3 | -- | **6** |
| Quads | -- | 10 | -- | 6 | **16** |
| Hamstrings | -- | 3 | -- | 7 | **10** |
| Biceps | 3 | -- | 3 | -- | **6** + row indirect = ~10 |
| Triceps | 3 | -- | 3 | -- | **6** + press indirect = ~10 |
| Calves | -- | 4 | -- | 4 | **8** |
| Glutes | -- | 7 | -- | 7 | **14** |

**Note:** These are starting (MEV) volumes for Meso 1 Week 1. Add 1-2 sets per muscle group per week across each mesocycle by adding sets to existing exercises or adding an extra set of myo-reps.

---

### 2.3 Exercise Guide (Form Cues + EMG Selection)

#### EMG-Optimized Exercise Selection by Target

**Lat Width:** Pull-ups, Lat Pulldown (vertical pull plane)
**Lat Thickness:** Barbell Row, Cable Row (horizontal pull plane)
**Upper Chest:** Incline DB Press at 30 degrees, Low-to-High Cable Fly
**Lateral Delt:** Cable Lateral Raise (constant tension), DB Lateral Raise with slight lean
**Rear Delt:** Incline Rear Delt Fly, Face Pulls with external rotation
**Bicep Long Head (peak):** Incline DB Curl (shoulder extended)
**Bicep Short Head (width):** Preacher Curl, Spider Curl
**Tricep Long Head:** Overhead Cable Extension (stretched position)
**Tricep Lateral Head:** Pushdown with V-bar
**VMO/Inner Quad:** Full-depth squats, Full-ROM leg extension

#### Form Cues (Top 3 Per Exercise)

**Barbell Squat:**
1. Brace core hard -- breath into belly before descending
2. Push knees out over toes, never let them cave
3. Break at hips and knees simultaneously, sit "between" legs

**Romanian Deadlift:**
1. Neutral spine throughout -- NEVER round lower back
2. Push hips back (hip hinge), hamstring stretch dictates depth
3. Bar stays in contact with thighs/shins -- vertical bar path

**Bench Press:**
1. Retract + depress scapulae ("shoulder blades in back pockets")
2. Bar touches lower chest, elbows at 45-75 degrees (not 90)
3. Drive feet into floor, press back toward rack (J-curve path)

**Overhead Press:**
1. Squeeze glutes + brace core to prevent back hyperextension
2. Press bar in straight line -- move head back, then push "through the window"
3. Bar starts on front delts/clavicle, not floating in front

**Barbell Row:**
1. 45-degree torso angle, flat back
2. Pull bar to lower chest/upper abdomen, elbows behind you
3. Control the eccentric -- no bouncing at bottom

**Pull-ups / Lat Pulldown:**
1. Depress scapulae first ("shoulder blades down") before bending elbows
2. Pull elbows down and slightly back toward hips
3. Full stretch at bottom, full contraction at top -- no partial ROM

**Lateral Raises:**
1. Keep shoulders depressed ("away from ears") -- if traps take over, weight is too heavy
2. Lead with elbows, slight bend, raise to shoulder height only
3. Slight forward lean aligns lateral delt better with gravity

**Face Pulls:**
1. Cable at face height, rope attachment
2. Pull toward face while externally rotating -- finish with hands beside ears
3. Keep elbows high (at or above shoulder height)

**Bicep Curl:**
1. Elbows pinned at sides -- no forward drift
2. Full ROM: full extension bottom, full squeeze top
3. Control eccentric 2-3 seconds

**Tricep Pushdown:**
1. Pin elbows to sides -- if shoulders move, lats are taking over
2. Full lockout at bottom, squeeze
3. Control the return -- don't let the stack yank hands up

#### Common Mistakes (Intermediates)

| Exercise | Mistake 1 | Mistake 2 |
|---|---|---|
| Squat | Knees caving inward | Rising hips-first (good morning squat) |
| RDL | Rounding lower back | Bar drifting away from body |
| Bench | Flaring elbows to 90 degrees | Losing scapular retraction mid-set |
| OHP | Excessive back arch | Pressing bar around head (curved path) |
| Row | Excessive torso rise/body English | Shrugging instead of rowing |
| Lateral Raise | Shrugging traps | Using momentum/swinging |
| Calf Raise | Bouncing with no pause at top | Insufficient stretch at bottom |

#### Video Resources

- **Jeff Nippard** -- EMG breakdowns, technique series
- **Renaissance Periodization** -- Muscle-specific exercise guides
- **Jeremy Ethier / Built With Science** -- Clean visual overlays
- **Squat University** -- Mobility + form analysis

#### Illustration Source

**free-exercise-db** (github.com/yuhonas/free-exercise-db) -- 800+ exercises, public domain, free for commercial use. GIF/image hotlinking available.

---

### 2.4 Nutrition Plan

#### Macro Targets (170-180 lb / 77-82 kg male)

**Lean Bulk (recommended):**

| Macro | Target | Per Meal (4-5 meals) |
|---|---|---|
| Calories | 2600-2900 kcal | ~520-725 per meal |
| Protein | 180-200g | 36-50g per meal |
| Carbs | 280-350g | 56-88g per meal |
| Fat | 65-85g | 13-21g per meal |

**Recomp (alternative):**
- Training days: maintenance calories (~2500), high carb
- Rest days: slight deficit (-200 kcal), lower carb
- Protein: 200-220g (higher than bulk to preserve muscle in deficit)

#### High-Protein Indian Meals (Top Picks)

| Meal | Serving | Protein | Calories | P:Cal Ratio |
|---|---|---|---|---|
| Tandoori Chicken Breast | 150g | 46g | 248 | BEST |
| Chicken Tikka (grilled) | 150g | 38g | 220 | Excellent |
| Goat Keema (dry) | 200g | 42g | 320 | Excellent |
| Egg Bhurji (6W + 2 whole) | 250g | 30g | 260 | Good |
| Fish Curry (cod, tomato) | 200g + gravy | 32g | 250 | Good |
| Moong Dal (1 cup cooked) | 200g | 14g | 180 | Supplemental |
| Masoor Dal (1 cup cooked) | 200g | 18g | 230 | Best dal for protein |

#### American/Fusion Meals

| Meal | Serving | Protein | Calories |
|---|---|---|---|
| Grilled chicken breast | 8 oz raw / 6 oz cooked | 53g | 280 |
| Baked salmon | 6 oz | 34g | 350 |
| Greek yogurt (Fage 0%) | 1 cup | 23g | 130 |
| Cottage cheese (low-fat) | 1 cup | 28g | 180 |
| Egg white scramble (6W + 2 whole) | 300g | 34g | 260 |

#### Sample Day: Indian Food Day (199g protein, ~2530 cal)

| Time | Meal | P | C | F | Cal |
|---|---|---|---|---|---|
| 7:30 AM | 4-egg masala omelette + 2 wheat parathas + chai | 28g | 48g | 24g | 520 |
| 10:30 AM | Moong dal cheela (2 medium) + mint chutney | 14g | 22g | 6g | 200 |
| 1:00 PM | 200g chicken tikka + 1 cup toor dal + 1 cup brown rice + raita | 58g | 72g | 14g | 680 |
| 4:30 PM (pre-workout) | Banana + 1 scoop whey | 27g | 30g | 2g | 230 |
| 7:30 PM (post-workout) | Goat keema (200g) + 2 rotis + palak sabzi | 48g | 52g | 18g | 620 |
| 10:00 PM | Greek yogurt + honey + 10 almonds | 24g | 22g | 12g | 280 |
| **TOTAL** | | **199g** | **246g** | **76g** | **2530** |

#### Sample Day: Hybrid Indian-American Day (200g protein, ~2650 cal)

| Time | Meal | P | C | F | Cal |
|---|---|---|---|---|---|
| 7:30 AM | 6 egg whites + 2 whole eggs scramble + spinach + 1 toast | 34g | 18g | 12g | 320 |
| 10:30 AM | 1 cup cottage cheese + berries | 29g | 12g | 3g | 210 |
| 1:00 PM | 8 oz tandoori chicken breast + 1.5 cup basmati rice + side salad | 55g | 80g | 10g | 700 |
| 4:30 PM | Whey shake + banana + 1 tbsp peanut butter | 30g | 38g | 10g | 330 |
| 7:30 PM | 6 oz baked salmon + sweet potato + steamed broccoli + 1/2 cup dal | 42g | 50g | 22g | 600 |
| 10:00 PM | Greek yogurt + casein scoop | 47g | 12g | 1g | 240 |
| **TOTAL** | | **237g** | **210g** | **58g** | **2400** |

*(Add rice/roti to hit 2600-2900 for lean bulk)*

#### Meal Timing Protocol

| Window | What | Macros |
|---|---|---|
| Pre-workout (60-90 min before) | Moderate protein + carbs, low fat (roti + chicken, rice + dal) | 30-40g P, 40-60g C, <10g F |
| Post-workout (within 2 hours) | High protein + carbs (chicken + rice, shake + banana) | 40-50g P, 40-80g C |
| Pre-bed | Slow protein (cottage cheese, casein, paneer) | 25-40g P |

**Key evidence:** Total daily protein intake matters far more than timing (Schoenfeld & Aragon meta-analysis). Distribute across 4-5 meals, ~35-50g each.

#### Grocery Lists

**Indian Store (Spice SPC Capitol Hill / India Bazaar Bellevue):**
- Proteins: Paneer, toor/moong/masoor/chana dal, frozen goat meat, frozen fish
- Carbs: Basmati rice (10 lb), whole wheat atta, frozen parathas, besan, poha
- Spices: Garam masala, turmeric, red chili, coriander, cumin, tandoori masala, curry leaves, ginger-garlic paste
- Other: Dahi/yogurt, ghee (small jar)

**Costco / Trader Joe's / QFC:**
- Proteins: Chicken breast (Kirkland 6.5 lb bag), eggs (5 dozen), salmon fillets, Greek yogurt (Fage 35 oz tub), cottage cheese, whey protein
- Carbs: Oats, sweet potatoes, brown rice, Dave's Killer Bread, bananas, frozen berries
- Fats: Almonds/walnuts (bulk), natural peanut butter, olive oil, avocados
- Vegetables: Spinach (fresh + frozen), broccoli (frozen), bell peppers, onions, tomatoes
- Snacks: Pre-peeled hard boiled eggs, string cheese, protein bars, tuna pouches, edamame

**Meal prep strategy:** Sunday cook 2 kg chicken breast (tandoori-spiced), a large pot of dal, and a pot of brown rice. Portion into 5-6 containers for weekday lunches.

---

### 2.5 Tracking System

#### Training Log Format

```
Date: ___  Session: Upper A  Week: __ / Meso: __

Exercise          | Set 1      | Set 2      | Set 3      | Set 4      | Notes
Bench Press       | 185x8 @3RIR| 185x8 @2   | 185x7 @1   | 185x6 @1   | Top of range on 3 sets -> +5 lbs next week
Barbell Row       | 155x10 @2  | 155x9 @2   | 155x8 @1   | 155x8 @1   |
Incline DB Press  | 55x11 @2   | 55x10 @1   | 55x9 @1    |            |
...
```

#### Nutrition Log

Track daily: total protein (must hit 180g+), total calories, bodyweight (morning, fasted).
Use MyFitnessPal or Cronometer (both have Indian food entries).
Weekly: review average bodyweight trend. Adjust calories if gaining >2 lb/month (reduce 100 cal) or not gaining (increase 100-200 cal).

---

## Phase 3: Tasks (Execution Plan)

### 3.1 Deliverables

| ID | Deliverable | Format | Agent Assignment |
|----|------------|--------|-----------------|
| D1 | Complete 12-week training program (all 48 sessions) | Markdown + PDF | Arjuna (SDE) |
| D2 | Exercise guide with form cues + illustrations | Markdown with image links | Nakula (FE) |
| D3 | Nutrition plan with 7-day meal rotation | Markdown + PDF | Draupadi (PM) |
| D4 | Grocery lists (Indian + American) | Markdown checklist | Draupadi (PM) |
| D5 | Training log template | Markdown table | Bhima (BE) |
| D6 | Quick-reference workout cards (1 page per session) | Markdown | Nakula (FE) |

### 3.2 Task Decomposition

| Task | Description | Depends On | Agent |
|------|------------|------------|-------|
| T1 | Write all 48 workout sessions (12 weeks x 4 days) with progressive overload mapped | Spec | Arjuna |
| T2 | Create exercise guide cards (illustration + 3 cues + 2 mistakes per exercise) | Spec | Nakula |
| T3 | Write 7-day meal rotation (4 Indian days + 3 hybrid days) with exact macros | Spec | Draupadi |
| T4 | Create grocery shopping checklist (Indian store + US store) | T3 | Draupadi |
| T5 | Build training log template (printable, one page per week) | T1 | Bhima |
| T6 | Create 4 quick-reference workout cards (1 per session, fits 1 page) | T1, T2 | Nakula |

### 3.3 Dependency Graph

```
T1 (workouts) -----> T5 (log template) -----> T6 (quick cards)
                                                    ^
T2 (exercise guides) ------------------------------/
T3 (meal plans) ----> T4 (grocery lists)
```

**Parallel tracks:**
- Track A: T1 + T2 (can run simultaneously)
- Track B: T3 (independent)
- After both complete: T4, T5, T6

### 3.4 Vajra Fleet Assignment

```
/vajra fleet iron-temple

Crew: Arjuna (lead) + Nakula + Draupadi + Bhima

Arjuna: T1 -- Write all 48 workout sessions
Nakula: T2 -- Exercise guide cards
Draupadi: T3 + T4 -- Meal plans + grocery lists
Bhima: T5 -- Training log template

After parallel phase: Nakula handles T6 (quick cards) using T1 + T2 outputs
```

### 3.5 Acceptance Tests

| Task | Test |
|------|------|
| T1 | All 48 sessions have exercises, sets, reps, RIR, rest. Volume ramps correctly across mesocycles. |
| T2 | Every exercise in T1 has a corresponding guide card with illustration link + 3 cues + 2 mistakes. |
| T3 | 7 days of meals. Every day hits 180-200g protein within 2500-2900 kcal. Macro math checks out. |
| T4 | Grocery list covers all ingredients in T3. Split by store type. |
| T5 | Log template has columns for exercise, weight, reps, RIR, notes. One page per week. |
| T6 | Each card fits one page. Contains exercise name, sets x reps, RIR, rest, form cue summary. |

---

## Appendix A: Research Sources

### Training Science
- Schoenfeld 2016 -- Training frequency meta-analysis (2x/week > 1x/week)
- Israetel/RP Strength -- Volume landmarks (MEV/MAV/MRV)
- 2025 Dose-response meta-regression -- Volume is dominant driver
- 2024 Bayesian meta-analysis -- Rest intervals (>60s beneficial, plateau at 90s)
- 2025 Superset meta-analysis -- 30-40% time savings, no hypertrophy penalty

### Nutrition
- Morton, Schoenfeld, Helms 2018 -- Protein plateau at 1.62 g/kg, CI to 2.2 g/kg
- ISSN Position Stand -- 1.4-2.0 g/kg for exercising individuals
- Schoenfeld & Aragon -- Nutrient timing revisited (total > timing)

### Exercise Science
- EMG studies for muscle targeting (delts, biceps, triceps, chest, back)
- free-exercise-db -- Public domain exercise illustrations
- wger -- Open source exercise database (CC-BY-SA)
