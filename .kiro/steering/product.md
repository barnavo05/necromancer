# Product: Necromancer

Necromancer brings dead COBOL code back to life.

Banks, insurers and governments still run on COBOL, and the people who understand it are retiring. Necromancer takes a legacy COBOL program and:

1. Exhume: parses it and explains what it does in plain English
2. Resurrect: translates it into clean, modern Python
3. Seance: runs the original COBOL and the new Python on hundreds of random inputs and proves they produce the same outputs (property-based testing). Any mismatch is shown as a "restless spirit" the user can inspect.

Target users: engineers and IT teams modernising legacy systems.
Hackathon: Kiroween 2026, Resurrection category.

The proof of equivalence is the core feature. Never present a translation as correct unless the seance has verified it.