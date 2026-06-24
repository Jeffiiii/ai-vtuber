# Elysia Agent Inbox

This file is your remote control. From anywhere (work laptop, phone), edit the **TODO**
section and `git push`. A scheduled job on the home PC pulls this hourly, does the work,
checks items off, writes results under **LOG**, and pushes back — so you can review when
you're home.

## How to use

- Add a task under TODO as a checkbox line: `- [ ] your instruction here`.
- Make each task **self-contained and specific** (the job starts with no memory of our
  chats). Mention file paths / which repo when it matters.
- Good: `- [ ] In add_vivid_examples.py, add 15 more 'hyper' English banter lines, then regenerate elysia_train_v2.jsonl and report the new counts.`
- Avoid destructive asks (deleting data, force-push). The job will skip anything risky and say why.
- The job only acts on **unchecked** `- [ ]` items; it ignores `- [x]` done ones.

## TODO

<!-- add your instructions below this line -->

- [ ] (example — delete me) Reply in the LOG with "inbox is live" and the current date, so I know the scheduled job works.

## LOG

<!-- the scheduled job appends dated results here -->
