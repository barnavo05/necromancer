# Requirements: Seance proof of equivalence

## Introduction

Necromancer translates COBOL to Python. The seance is the core feature: it runs the original COBOL and the Python translation on many generated inputs and compares every output. A translation is only ever shown as correct when the seance has verified it.

## Requirements

### Requirement 1: Compare COBOL and Python on generated inputs

**User Story:** As an engineer modernising a legacy program, I want both programs run on many inputs, so that I can trust the translation without reading every line.

#### Acceptance Criteria

1. WHEN the user starts a seance with a COBOL program, a Python program and an input spec, THE SYSTEM SHALL compile and run the COBOL with GnuCOBOL and run the Python on the same generated inputs.
2. THE SYSTEM SHALL generate 200 cases by default, and SHALL accept between 1 and 500.
3. WHEN every output matches, THE SYSTEM SHALL report the run as Verified with the number of matched cases.
4. IF the COBOL fails to compile or the Python cannot run, THEN THE SYSTEM SHALL return a clear error and SHALL NOT report Verified.

### Requirement 2: Respect COBOL number rules

**User Story:** As an engineer, I want inputs that stay inside what each COBOL field can hold, so that silent COBOL truncation is not mistaken for a translation bug.

#### Acceptance Criteria

1. THE SYSTEM SHALL generate each input inside the range given in the input spec.
2. THE SYSTEM SHALL pass inputs as plain decimal text, and programs SHALL read them with ACCEPT into a text field plus FUNCTION NUMVAL.
3. WHEN a program is pasted without an input spec, THE SYSTEM SHALL infer the input fields and ranges from its data division, and the user SHALL be able to edit them.

### Requirement 3: Hunt boundaries

**User Story:** As an engineer, I want edge cases tested, so that off by one mistakes at thresholds are found.

#### Acceptance Criteria

1. THE SYSTEM SHALL read numeric constants from the COBOL procedure division and include each constant, and one step either side, in the generated cases.

### Requirement 4: Show and shrink failures

**User Story:** As an engineer, I want mismatches shown clearly and made small, so that I can see why a translation is wrong.

#### Acceptance Criteria

1. WHEN an output differs, THE SYSTEM SHALL show it as a restless spirit with the COBOL and Python outputs side by side.
2. WHEN failures exist, THE SYSTEM SHALL shrink to the smallest failing input and show it.
3. THE SYSTEM SHALL cap the number of COBOL failures it processes so a broken program cannot run forever.

### Requirement 5: Test the tester (Haunt)

**User Story:** As an engineer, I want proof the seance can actually catch bugs, so that Verified means something.

#### Acceptance Criteria

1. WHEN the user starts a haunt on a translation that already passes, THE SYSTEM SHALL inject up to 12 bugs into the Python and report how many the seance catches.
2. WHEN an injected bug survives the first run, THE SYSTEM SHALL retry it with 500 extra random inputs before calling it survived.
3. IF the translation does not pass the seance, THEN THE SYSTEM SHALL refuse to haunt it.
4. THE SYSTEM SHALL list survivors honestly.

### Requirement 6: Certificate and Autopsy

**User Story:** As an engineer, I want a record of what was verified and a list of the traps in my program, so that I can show the result to others.

#### Acceptance Criteria

1. WHEN a run is Verified, THE SYSTEM SHALL offer a downloadable certificate with SHA 256 hashes of both programs, the input ranges, the edge cases and the compiler version.
2. THE SYSTEM SHALL list the statements in a COBOL program that commonly break a translation (such as truncation, rounding and loop counters that wrap).
