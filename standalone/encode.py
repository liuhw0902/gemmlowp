# Copyright 2018 The gemmlowp Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""
Encodes ARM asm code for certain instructions into the corresponding machine
code encoding, as a .word directive in the asm code, preserving the original
code in a comment.

Reads from stdin, writes to stdout.

Example diff:
-        "udot v16.4s, v4.16b, v0.16b\n"
+        ".word 0x6e809490  // udot v16.4s, v4.16b, v0.16b\n"

The intended use case is to make asm code easier to compile on toolchains that
do not support certain new instructions.
"""

import sys
import re


def encode_udot_vector(line):
  m = re.search(
      r'\budot[ ]+v([0-9]+)[ ]*.[ ]*4s[ ]*,[ ]*v([0-9]+)[ ]*.[ ]*16b[ ]*,[ ]*v([0-9]+)[ ]*.[ ]*16b',
      line)
  if not m:
    return 0, line

  match = m.group(0)
  accum = int(m.group(1))
  lhs = int(m.group(2))
  rhs = int(m.group(3))
  assert accum >= 0 and accum <= 31
  assert lhs >= 0 and lhs <= 31
  assert rhs >= 0 and rhs <= 31
  mcode = 0x6e809400 | (accum << 0) | (lhs << 5) | (rhs << 16)
  return mcode, match


def encode_udot_element(line):
  m = re.search(
      r'\budot[ ]+v([0-9]+)[ ]*.[ ]*4s[ ]*,[ ]*v([0-9]+)[ ]*.[ ]*16b[ ]*,[ ]*v([0-9]+)[ ]*.[ ]*4b[ ]*\[([0-9])\]',
      line)
  if not m:
    return 0, line

  match = m.group(0)
  accum = int(m.group(1))
  lhs = int(m.group(2))
  rhs = int(m.group(3))
  lanegroup = int(m.group(4))
  assert accum >= 0 and accum <= 31
  assert lhs >= 0 and lhs <= 31
  assert rhs >= 0 and rhs <= 31
  assert lanegroup >= 0 and lanegroup <= 3
  l = 1 if lanegroup & 1 else 0
  h = 1 if lanegroup & 2 else 0
  mcode = 0x6f80e000 | (accum << 0) | (lhs << 5) | (rhs << 16) | (l << 21) | (
      h << 11)
  return mcode, match


def encode(line):
  for encode_func in [encode_udot_vector, encode_udot_element]:
    mcode, match = encode_func(line)
    if mcode:
      return mcode, match
  return 0, line


def read_existing_encoding(line):
  m = re.search(r'\.word\ (0x[0-9a-f]+)', line)
  if m:
    return int(m.group(1), 16)
  return 0


lineno = 0
found_existing_encodings = False
found_error = False
for line in sys.stdin:
  lineno = lineno + 1
  mcode, match = encode(line)
  if mcode:
    existing_encoding = read_existing_encoding(line)
    if existing_encoding:
      found_existing_encodings = True
      if mcode != existing_encoding:
        sys.stderr.write(
            "Error at line %d: existing encoding 0x%x differs from encoding 0x%x for instruction '%s':\n\n%s\n\n"
            % (lineno, existing_encoding, mcode, match, line))
        found_error = True
    else:
      line = line.replace(match, '.word 0x%x  // %s' % (mcode, match))
  sys.stdout.write(line)
if found_error:
  sys.exit(1)
if found_existing_encodings:
  sys.stderr.write(
      'Note: some instructions that this program is able to encode, were already encoded. These encodings have been checked.\n'
  )
