# Requirements: Exhume, Resurrect and Exorcise (model assisted steps)

## Introduction

Three steps use a language model: explaining the COBOL, translating it to Python, and repairing a translation that fails the seance. The model is called from the server only. The seance, not the model, decides whether a translation is correct.

## Requirements

### Requirement 1: Exhume

**User Story:** As an engineer, I want a plain English explanation of a COBOL program, so that I understand it before I trust a translation.

#### Acceptance Criteria

1. WHEN the user exhumes a bundled sample, THE SYSTEM SHALL return the bundled explanation and SHALL NOT need an API key.
2. WHEN the user exhumes their own program, THE SYSTEM SHALL ask the model for an explanation paragraph by paragraph.
3. WHEN the user hovers a paragraph in the explanation, THE UI SHALL scroll the green screen to that paragraph.

### Requirement 2: Resurrect

**User Story:** As an engineer, I want the program translated to Python, so that I can run and test it.

#### Acceptance Criteria

1. WHEN the user resurrects a bundled sample, THE SYSTEM SHALL return the bundled translation.
2. WHEN the user resurrects their own program, THE SYSTEM SHALL ask the model for Python that uses `Decimal` for money, SHALL strip any code fences from the reply, and SHALL reject a reply that has no `main` function.
3. THE SYSTEM SHALL show the translation as unverified until the seance passes.
4. THE SYSTEM SHALL let the user edit the Python and run the seance on their edit.

### Requirement 3: Exorcise

**User Story:** As an engineer, I want the model to repair a failing translation using the failures as feedback, so that I do not have to debug by hand.

#### Acceptance Criteria

1. WHEN the user starts an exorcise, THE SYSTEM SHALL run the seance, and IF it is not Verified THEN THE SYSTEM SHALL send the COBOL, the Python and the first 5 restless spirits to the model for a repair.
2. THE SYSTEM SHALL run the seance for at most 3 rounds by default, and at most 5. A round is one seance run, so a request for N rounds makes at most N minus 1 repairs, and the last round is never repaired.
3. THE SYSTEM SHALL return each round with its matched count and its smallest failing input.
4. WHEN a round is Verified, THE SYSTEM SHALL stop and report how many rounds it took.
5. IF the last round is still not Verified, THEN THE SYSTEM SHALL say so and keep showing the restless spirits.

### Requirement 4: Keys and model availability

**User Story:** As the maintainer, I want the key kept off the browser and the model calls to survive a busy provider, so that the demo does not break.

#### Acceptance Criteria

1. THE SYSTEM SHALL read the key, base URL and model list from environment variables, and `.env.example` SHALL document them. A free OpenAI compatible provider (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`) is used when its key and URL are set, otherwise `ANTHROPIC_API_KEY` is used (with `ANTHROPIC_MODEL` optional).
2. THE SYSTEM SHALL try each model in a comma separated list in order.
3. WHEN the provider answers 429, 500, 502, 503 or 504 and only one model is configured, THE SYSTEM SHALL retry up to 3 times, waiting 2, 5 and 10 seconds. WHEN several models are configured, THE SYSTEM SHALL move to the next model straight away, so a busy model does not stall the demo.
4. IF every model fails, THEN THE SYSTEM SHALL answer 503 with a readable message.
5. WHEN no key is set, THE SYSTEM SHALL still allow bundled samples and the seance.
