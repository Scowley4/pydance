# Contains filters for the various modifiers possible

import random, math, games, copy

NOT_STEPS = ["D", "S", "L", "W", "B", "R"]

# 0 - Normal
# 1 - Mirror
# 2 - Left
# 3 - Right
# -1 - Shuffle, -2 - random

# Map A to B using table C; A[i] -> B[C[i]].
# FIXME: Use direction strings here... They're simpler.
STEP_MAPPINGS = {
  "SINGLE": [[0, 1, 2, 3], [3, 2, 1, 0], [1, 3, 0, 2], [2, 0, 3, 1]],
  "5PANEL": [[0, 1, 2, 3, 4], [3, 4, 2, 0, 1], [4, 0, 2, 1, 3],
             [1, 3, 2, 4, 5]],
  "PARAPARA": [[0, 1, 2, 3, 4], [1, 0, 2, 4, 3], [4, 0, 1, 2, 3],
               [1, 2, 3, 4, 0]],
  "6PANEL": [[0, 1, 2, 3, 4, 5], [4, 5, 3, 2, 0, 1], [2, 0, 5, 1, 3, 4],
             [1, 3, 0, 4, 5, 2]],
  "8PANEL": [[0, 1, 2, 3, 4, 5, 6, 7], [5, 6, 7, 4, 3, 0, 1, 2],
             [3, 0, 1, 7, 2, 4, 5, 6], [1, 2, 4, 0, 5, 6, 7, 3]],
  "9PANEL": [[0, 1, 2, 3, 4, 5, 6, 7, 8], [6, 7, 8, 5, 4, 3, 0, 1, 2],
             [3, 0, 1, 8, 4, 2, 5, 6, 7], [1, 2, 5, 0, 4, 6, 7, 8, 3]],
  "DMX": [[0, 1, 2, 3], [2, 3, 0, 1], [3, 0, 1, 2], [1, 2, 3, 0]],
  "EZ2SINGLE": [[0, 1, 2, 3, 4], [4, 3, 2, 1, 0], [4, 3, 2, 1, 0],
                [4, 3, 2, 1, 0]],
  "EZ2REAL": [[0, 1, 2, 3, 4, 5, 6], [6, 4, 5, 3, 1, 2, 0],
              [3, 2, 4, 6, 1, 5, 0], [6, 4, 1, 0, 2, 5, 3]],
  
  }

MAP_EQUIVS = {
  "SINGLE": ["DOUBLE", "COUPLE", "VERSUS"],
  "5PANEL": ["5DOUBLE", "5COUPLE", "5VERSUS"],
  "6PANEL": ["6DOUBLE", "6COUPLE", "6VERSUS"],
  "8PANEL": ["8DOUBLE", "8COUPLE", "8VERSUS"],
  "9PANEL": ["9DOUBLE", "9COUPLE", "9VERSUS"],
  "PARAPARA": ["PARADOUBLE", "PARACOUPLE", "PARAVERSUS"],
  "EZ2SINGLE": ["EZ2VERSUS", "EZ2DOUBLE", "EZ2COUPLE"],
  "EZ2REAL": ["REALVERSUS", "REALCOUPLE", "REALDOUBLE"],
  }

for mode, equivs in MAP_EQUIVS.items():
  for eq in equivs: STEP_MAPPINGS[eq] = STEP_MAPPINGS[mode]

# This is a pseudorandom number generator that we're guaranteed will
# always return the same results between different versions of Python,
# given the same seed. This makes sure the same autogenerated steps are
# made across different versions and platforms.

# A) Never change these numbers; they do ensure good randomness.
# B) Never use this module anywhere except pydance; its randomness is bad.
class NonRandom(random.Random):
  def __init__(self, seed = 1):
    self.seed(seed)
    self.m = 16807
    self.n = 2147483647

  def getstate(self): return self.seed

  def setstate(self, state): self.seed(state)

  def seed(self, seed = 1): self.seed = seed

  def jumpahead(self, n): pass

  def random(self):
    self.seed = (self.seed * self.m) % self.n
    return float(self.seed) / self.n
  
# General step transformation class. By default, identity transform.
class Transform(object):
  def __init__(self, *args): pass
  
  def transform(self, steps):
    return [self._update_state(s) or self._transform(s) for s in steps]

  def _update_state(self, s): pass

  def _transform(self, s): return list(s)

# Compress the steps to remove empty lines. FIXME: Do this in fileparsers.
def compress(steps):
  new_steps = []
  beat_count = 0
  last_event = None
  for s in steps:
    if not isinstance(s[0], float): # Not a step
      if last_event is not None: new_steps.append([beat_count] + last_event)
      last_event = None
      beat_count = 0
      new_steps.append(s)
    elif s[1:].count(0) != (len(s) - 1) or last_event == None: # Non-empty
      if last_event is not None: new_steps.append([beat_count] + last_event)
      last_event = s[1:]
      beat_count = s[0]
    else: # Empty event
      beat_count += s[0]

  if last_event is not None: new_steps.append([beat_count] + last_event)

  return new_steps

# Rotation, mirroring, shuffle, and random.
class MappingTransform(Transform):
  def __init__(self, mode, opt):
    self._mapping = STEP_MAPPINGS[mode][opt][:]

  def _transform(self, steps):
    if steps[0] not in NOT_STEPS:
      steps = steps[:]
      step = steps[1:]
      for j,s in enumerate(step): steps[self._mapping[j] + 1] = s
      return steps
    else:
      return steps[:]

class MirrorTransform(MappingTransform):
  def __init__(self, mode): MappingTransform.__init__(self, mode, 1)

class LeftTransform(MappingTransform):
  def __init__(self, mode): MappingTransform.__init__(self, mode, 2)

class RightTransform(MappingTransform):
  def __init__(self, mode): MappingTransform.__init__(self, mode, 3)

class ShuffleTransform(MappingTransform):
  def __init__(self, mode):
    MappingTransform.__init__(self, mode, 0)
    random.shuffle(self._mapping)

class RandomTransform(ShuffleTransform):
  def __init__(self, mode):
    ShuffleTransform.__init__(self, mode)
    self._holds = []

  def _update_state(self, steps):
    if steps[0] not in NOT_STEPS:
      if len(self._holds) == 0: random.shuffle(self._mapping)
      for i,s in enumerate(steps[1:]):
        if s & 1 and i in self._holds: self._holds.remove(i)
        if s & 2: self._holds.append(i)

rotate = [Transform, MirrorTransform, LeftTransform, RightTransform,
          RandomTransform, ShuffleTransform]

# Apply myriad additions/deletions to the step pattern
# FIXME: Return a list rather than in-place modify.
# Shit this is ugly because of that.
def size(steps, opt):
  if opt == 1: little(steps, 4) # Tiny
  elif opt == 2: little(steps, 2) # Little
  elif opt == 3: insert_taps(steps, 4.0, 2.0, False) # Big
  elif opt == 4: insert_taps(steps, 2.0, 1.0, False) # Quick
  elif opt == 5: insert_taps(steps, 4.0, 3.0, True) # Skippy

# Remove steps that aren't on the beat
def little(steps, mod):
  beat = 0.0
  # We have to be careful here to end hold arrows at the correct time,
  # even if the end falls on an off-beat. Otherwise they can run off into
  # infinity.
  holds = []
  for s in steps:
    if s[0] not in NOT_STEPS:
      old_s = s[:]
      if beat % mod != 0:
        s[1:] = [0] * (len(s) - 1)
      for i in holds[:]:
        if old_s[i] & 1:
          s[i] |= 1
          holds.remove(i)
      beat += s[0]
      for i,si in enumerate(s[1:]):
        if i not in holds and si & 2: holds.append(i)

    elif s[0] == "D": beat += s[1]

# Insert taps if a note falls on a interval-even beat, and the next step
# is interval-away. Insert the new step offset away from the original step
# (and therefore the time for the offset set is interval - offset).
# not_same makes sure the random tap inserted isn't the same as either of
# the surrounding ones.

# Inspired by Stepmania's function of the same name, in src/NoteData.cpp.
def insert_taps(steps, interval, offset, not_same):
  new_steps = []
  holds = []
  beat = 0.0
  rand = NonRandom(int(interval * offset * len(steps)))
  for i,step in enumerate(steps[:-1]):
    if isinstance(step[0], float): # This is a note...
      for j,s in enumerate(step[1:]):
        if s & 2: holds.append(j)
        elif s & 1 and j in holds: holds.remove(j)
      
      if not isinstance(steps[i + 1][0], float):
        new_steps.append(step) # Next isn't a note.

      elif (step[1:].count(0) == len(step[1:]) or
            steps[i + 1][1:].count(0) == len(steps[i + 1][1:])):
        # The surrounding notes are both empty.
        new_steps.append(step)

      elif len(holds) > 1: # Don't add things during two holds
        new_steps.append(step)

      elif step[0] == interval and beat % interval == 0: # Bingo!
        step = steps[i][0] = offset
        beat += offset
        new_steps.append(step)

        if not_same:
          start = rand.randint(0, len(steps[i][1:]) -1)
          empty = [0] * len(step[1:])
          for j in range(len(step[1:])):
            checking = (start + j) % len(step[1:])
            if not (step[checking + 1] or steps[i + 1][checking + 1]):
              empty[checking] = 1
              break
          new_steps.append([interval - offset] + empty)
        else:
          new_step = [1] + ([0] * (len(steps[i][1:]) - 2))
          rand.shuffle(new_step)
          new_steps.append([interval - offset] + new_step)

      else: new_steps.append(steps[i])

      beat += new_steps[-1][0]
      # Stupid inaccurate floating point.
      if int(beat + 0.00001) > int(beat): beat = int(beat + 0.00001)
    else:
      if steps[i][0] == "D": beat += steps[i][1]
      new_steps.append(steps[i])

  steps[0:-1] = new_steps # Copy into place.

# Pretty obvious.
class RemoveHoldTransform(Transform):
  def _transform(self, s):
    if s[0] not in NOT_STEPS: return [s[0]] + [i & 13 for i in s[1:]]
    else: return s[:]

# Remove secret steps; defined by the 4 bit being on, so 5, 6, or 7.
class RemoveSecret(Transform):
  def _transform(self, s):
    s = s[:]
    if s[0] not in NOT_STEPS:
      for i,si in enumerate(s[1:]):
        if si & 4: si = s[i] = 0
    return s

class RemoveJumps(Transform):
  def __init__(self):
    self._side = 0
    self._holds = []

  def _transform(self, s):
    if s[0] not in NOT_STEPS:
      step = s[1:]
      for i,s in enumerate(step):
        if s & 2 and i not in self._holds: self._holds.append(i)

      if step.count(0) < len(step) - 1:
        if self._side and not self._holds: step.reverse()
        for i,stepi in enumerate(step):
          if stepi:
            step[i] = 0
            break
        if self._side and not self._holds: step.reverse()
        self._side ^= 1

      for i,s in enumerate(step):
        if s & 1 and not s & 2 and i in self._holds:
          self._holds.remove(i)

      return [s[0]] + step
    else: return s[:]

# Add jumps to on-beats with steps.
class WideTransform(Transform):
  def __init__(self):
    self._beat = 0.0
    self._holds = []

  def _update_state(self, s):
    if s[0] not in NOT_STEPS:
      for i,si in enumerate(s[1:]):
        if si & 1 and i in self._holds: self._holds.remove(i)

  def _transform(self, s):
    if s[0] not in NOT_STEPS:
      step = s[1:]
      if (self._beat % 4 == 0 and s.count(0) == len(step) - 1 and
          len(self._holds) == 0):
        first = 0
        while step[first] == 0: first += 1 # Find the first step
        to_add = int(math.sqrt(self._beat)) % len(step)
        if step[to_add] != 0: to_add = (to_add + 1) % len(step)
        step[to_add] = 1
        s = [s[0]] + step

      for i,si in enumerate(s[1:]):
        if si & 2: self._holds.append(i)

      self._beat += s[0]
    elif s[0] == "D": beat += s[1]
    return s[:]

jumps = [RemoveJumps, Transform, WideTransform]

# Now, here's where stuff gets tricky. We have to randomly but
# deterministically generate fun steps for modes not in the file.
# Transform step patterns from N panel to M panel, M >= N.
class PanelTransform(Transform):

  # key is a direction; value is a list of directions that are "fun" to
  # map to. Repeating a direction makes it more likely to be chosen. No
  # direction should map to itself; making that extra-likely is taken
  # care of in the map generation algorithm already.
  accept = { "k": "uullc", "u": "kkzzc", "z": "uurrc",
             "l": "kkwwc", "c": "lluuddrrkzwg", "r": "zzggc",
             "w": "llddc", "d": "wwggc", "g": "ddrrc" }

  def __init__(self, orig_panels, new_panels, rand, freq = 0.075):
    self.orig_panels = orig_panels
    self.new_panels = new_panels
    self.freq = freq
    self.rand = rand # A NonRandom instance preseeded.

    # This is the chance (increasing by 'freq' for each datum we process)
    # that a new pseudorandom mapping table (see below) will be generated,
    # when a data transform is requested.

    self.count = 0

    # This is true if we encounter the same (exact) pattern twice in a row.
    # We never generate a new mapping table in such a case, and so preserve
    # multiple taps on the same arrow.
    self.repeating = False

    # This tracks the last two patterns transformed.
    self.last_processed = [None, None]

    # A dictionary mapping directions (characters) to a list of directions
    # (strings), that are a) "near" the original direction, and b) in
    # self.new_panels.
    self.accept = self._generate_accept()

    # A list of directions in orig_panels currently behind held.
    self.holds = []

    self._generate_transform()

  # Reduce the acceptable mapping table to only include directions from the
  # game modes in question.
  def _generate_accept(self):
    accept = {}
    for dir in PanelTransform.accept:
      if dir in self.orig_panels:
        accept[dir] = "".join([c for c in PanelTransform.accept[dir]
                               if c in self.new_panels])
    for dir in self.orig_panels:
      if not accept.has_key(dir):
        accept[dir] = "".join(self.new_panels)
    return accept

  # transform_mapping (trans) is, essentially, a scrambled list of directions
  # from orig_panels, but shoved into an array the size of new_panels.
  def _generate_transform(self):
    unmapped = list(self.orig_panels)
    trans = [None] * len(self.new_panels)

    # First, map any hold arrows to the same place they were in for the
    # last transformation, so they end at the right time.
    for d in self.holds:
      if d in self.transform_mapping:
        unmapped.remove(d)
        trans[self.transform_mapping.index(d)] = d

    # Next, give a high chance that any direction will be mapped
    # to itself, assuming it exists in the new panels. Or, always map
    # it to its old self, if no alternatives exist.

    # Originally, the "high chance" was hard coded around 0.5 to 0.75.
    # Lower values meant steps got shuffled more than desired on small
    # mappings, but higher ones resulted in small->large mappings not
    # using many of the available arrows. So, now the chance is the
    # ratio between the two sizes.

    chance = float(len(self.orig_panels)) / float(len(self.new_panels))
        
    unmapped_original = list(unmapped) # Don't modify the iterating list
    for d in unmapped_original:
      if d in self.new_panels:
        if self.rand.random() < chance or len(self.accept[d]) == 0:
          trans[self.new_panels.index(d)] = d
          unmapped.remove(d)

    # Next, go through whatever is left, and map it acceptably.
    for d in unmapped:
      accept = [a for a in self.accept[d] if
                trans[self.new_panels.index(a)] is None]

      if len(accept) != 0:
        dir = self.rand.choice(accept)
        trans[self.new_panels.index(dir)] = d
      else:
        # If possible, see if we can map to the original direction again
        # (all its neighbors may have gotten overwritten between the first
        # check and now).
        if d in self.new_panels and trans[self.new_panels.index(d)] is None:
          trans[self.new_panels.index(d)] = d

        # And finally --
        # Arrows in this direction won't get mapped to anything.
        # However, in order to avoid accidentally dropping many events
        # through poorly generated mappings, generate a new one more
        # quickly if this situation occurs.
        else: self.count = self.freq * 5

    self.transform_mapping = trans

  # Update our internal state based on the data passed in.
  def _update_state(self, steps):
    # This is a delay / BPM change / etc
    if not isinstance(steps[0], float): return

    self.count += self.freq * steps[0]

    # Check the last two events to see if this is a repeat.
    self.repeating = False
    if steps[1:] in self.last_processed:
      self.repeating = True
    self.last_processed.append(steps[1:])
    self.last_processed.pop(0)

    # If we're not repeating, see if it's time to generate a new
    # transformation table.
    if not self.repeating:
      if self.count > self.rand.random():
        self.count = 0
        self._generate_transform()

    # Note any holds, so they don't get remapped in the middle.
    for i,s in enumerate(steps[1:]):
      if s & 2:
        self.holds.append(self.orig_panels[i])
      elif s & 1 and self.orig_panels[i] in self.holds:
        self.holds.remove(self.orig_panels[i])

  # Actually perform the transformation on the data.
  def _transform(self, steps):
    # This is not a note, it's a BPM change / delay / etc
    if not isinstance(steps[0], float): return list(steps)

    new_steps = [0] * (len(self.transform_mapping) + 1)
    new_steps[0] = steps[0]

    for i,s in enumerate(steps[1:]):
      if s and self.orig_panels[i] in self.transform_mapping:
        new_steps[self.transform_mapping.index(self.orig_panels[i]) + 1] = s

    return new_steps

# This lets us cover the common case of DDR steps for KSF files, and avoid
# losing steps in the downscaling.
class FiveToFourTransform(Transform):

  def __init__(self, orig_panels, new_panels, rand):
    self.holding_center = False
    self.rand = rand # A NonRandom instance preseeded.

  def _update_state(self, steps):
    if not isinstance(steps[0], float): return
    if steps[3] & 2: holding_center = True
    elif steps[3] & 1: holding_center = False

  def _transform(self, steps):
    if not isinstance(steps[0], float): return list(steps)
    new_steps = [steps[0], steps[1], steps[2], steps[4], steps[5]]

    if 0 in new_steps:
      possible = [i for i,new_step in enumerate(new_steps) if new_step == 0]
      new_steps[self.rand.choice(possible)] |= steps[3]
    return new_steps

# Transform a song's steps from one mode and difficulty to a target mode.
def generate_mode(song, difficulty, target_mode, pid):
  equiv = {"SINGLE": "5PANEL", "VERSUS": "5VERSUS",
           "COUPLE": "5COUPLE", "DOUBLE": "5DOUBLE" }

  if target_mode in games.SINGLE: mode = "SINGLE"
  elif target_mode in games.VERSUS: mode = "VERSUS"
  elif target_mode in games.ONLY_COUPLE: mode = "COUPLE"
  elif target_mode in games.DOUBLE: mode = "DOUBLE"

  if song.steps.has_key(mode):
    # Dance ManiaX can be found as DWI files, with exact visual mappings.
    # Cheat and use that.
    if target_mode[:3] == "DMX":
      if target_mode in games.COUPLE:
        return song.steps[mode][difficulty][pid]
      else: return song.steps[mode][difficulty]

    steps = song.steps[mode][difficulty]
    T = PanelTransform
  elif song.steps.has_key(equiv[mode]):
    steps = song.steps[equiv[mode]][difficulty]
    mode = equiv[mode]
    if len(games.GAMES[target_mode].dirs) == 4: T = FiveToFourTransform
    else: T = PanelTransform
  else: print "This shouldn't happen! Email pyddr-devel@icculus.org."

  if mode in games.COUPLE: steps = steps[pid]

  seed = song.info["bpm"]
  if song.info["gap"] != 0: seed *= song.info["gap"]

  trans = T(games.GAMES[mode].dirs, games.GAMES[target_mode].dirs,
            NonRandom(int(song.info["bpm"])))

  return trans.transform(steps)