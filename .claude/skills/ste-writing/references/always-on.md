# Always-on STE

A skill cannot post-process every reply. Claude consults a skill when the task matches
the skill description, so a skill covers the deliberate cases: "rewrite this README",
"review this for slop", "lint this draft". It does not cover the ambient case, which is
every ordinary answer in every chat.

Two Claude.ai settings do cover the ambient case. Both hold the mechanical subset of the
rules, not the whole skill. The skill stays useful for real rewrite, review, and lint work,
because a settings field cannot run the linter.

- **Profile preferences** (Settings, "What preferences should Claude consider in
  responses?") apply to every conversation on the account. There is no per-chat toggle.
- **Custom styles** control how Claude formats and delivers a response, and you can switch
  them mid-conversation. This is the better home if you want STE on for docs and off for a
  brainstorm.
- **Claude Code** reads `CLAUDE.md` from the project root at the start of a session. Paste
  the same block there for terminal work.

Use one of the two, not both. Two copies of the same rules waste context and drift apart.

## The block

Paste this text into the preferences field, into a custom style, or into `CLAUDE.md`.

```
Write prose in Simplified Technical English (ASD-STE100).

- Use the short common word: start, use, help, make sure, do, give, before, after,
  about, get, show, also.
- Active voice. One idea per sentence.
- Simple tenses only. No present perfect, no stacked modals.
- No semicolons. No em dash or en dash as a dash. Use a period, a comma, a colon,
  or parentheses.
- No contractions.
- No marketing adjectives: seamless, robust, powerful, comprehensive, elegant.
- No phrasal verbs: spin up, dive into, kick off, roll out.
- No nominalizations. Write "analyze the log", not "perform an analysis of the log".
- One name for one thing. Do not rotate synonyms for the same action.
- Multi-word nouns: three words maximum.
- One topic per paragraph, six sentences maximum.
- No word count cap on a sentence. Keep the sentence that carries the idea. Split a
  sentence because it holds two ideas, not because it is long.

This governs prose only. Do not apply it to code, identifiers, command syntax, config
files, log output, error strings, filenames, URLs, quoted material, or test data. Inside
a code block, write normal idiomatic code and normal code comments. Never rename a
variable, a function, a flag, or a field to satisfy a word rule. Prose about code still
follows the rules.

Drop these rules for marketing copy, a speech, a personal message, or anything that needs
a voice. STE strips voice on purpose.
```

## What this changes and what it costs

The block removes the mechanical markers: the dashes, the hedges, the nominalizations, the
rotated synonyms. It cannot supply the thing that makes prose worth reading. A hollow
paragraph in clean STE is still hollow.

It also flattens replies you may not want flat. Explanations lose their analogies, and a
long chain of reasoning reads as a list of short assertions. If that becomes a problem,
move the block from preferences into a style so you can switch it off for one chat.

The block has no sentence length cap, and that is deliberate. Chat is not a procedure. A
hard cap in an always-on setting produces a staccato voice that reads worse than the slop
it replaced, and it fights the code carve-out, because one sentence that names a long
identifier can pass 25 words with no filler in it. The document rules still hold the caps
at 20 and 25 words. Ask for the skill by name when you want them applied.

The rules that do the work here are the word choices, the dashes, and the tense discipline.
Those are what mark a sentence as machine-written. Length is not.
