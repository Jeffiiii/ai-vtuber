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
- [ ] Check if the following problems do exist and actually need to be fixed: The most serious cluster covers things that can corrupt a run or quietly mask overfitting. The base-model inconsistency lives across sft_lora.py, which defaults to Qwen3-4B, and every eval and merge example, which use Qwen2.5-3B-Instruct; because a LoRA adapter only fits the base it was trained against, a mismatch either crashes on a shape error or silently produces garbage, so the fix is to assert args.base_model equals peft_cfg.base_model_name_or_path in post_train_health_check.py and make the base consistent everywhere. The thinking-mode problem is in eval_utils.py, where build_chat_text() omits enable_thinking=False even though sft_lora.py strips thinking during training; this means you score a different behavior than you trained and the <think> text leaks into the response string, inflating the length and character checks and eating the token budget, so pass enable_thinking=False with a try/except TypeError fallback for non-Qwen3 bases. Still in the critical tier, the lack of a validation set is in sft_lora.py: everything loads as one train split, so only training loss is visible and you can't tell whether 0.35 is genuine convergence or overfitting, and you end up saving the final, possibly overfit, epoch — fixable by adding train_test_split(test_size=0.1, seed=42) and setting eval_strategy="epoch", load_best_model_at_end=True, and metric_for_best_model="eval_loss". Related, also in sft_lora.py, the DataCollatorForLanguageModeling(mlm=False) computes loss over the whole sequence, including prompt and repeated template tokens that the model memorizes almost instantly, which deflates the 0.35 and spends adapter capacity on non-voice text; switch to DataCollatorForCompletionOnlyLM keyed on the assistant turn marker, or mask the prompt labels to -100. The next pair explains why a "passing" model can still feel under expectation. The rubric in eval_utils.py (row_passes() and basic_checks()) only checks language, prompt leakage, markdown, and length, so a bland, off-voice, or repetitive reply passes cleanly — it's blind to the exact symptom you started with, and the remedy is to add a quality signal such as an LLM-as-judge score, a repetition metric like distinct-2, or a manual spot-read. Compounding that, generate_one in eval_utils.py defaults to temperature=0.2 (echoed in heavy_ab_eval_lora.py, post_train_health_check.py, and test_merged_hf_model.py), which is near-greedy; Qwen3 tends to repeat at low temperature and a 0.2 eval won't reflect a VTuber served around 0.7–1.0, so use Qwen3's non-thinking parameters (roughly temperature 0.7, top_p 0.8, top_k 20, with a small presence penalty) or simply evaluate at your real serving settings. The remaining items are hygiene rather than breakage. The tokenizer is loaded inconsistently — heavy_ab_eval_lora.py pulls it from the base model while post_train_health_check.py pulls it from the adapter — and since training saved the tokenizer alongside the adapter, the base one can mismatch the chat template or special tokens, so load it from the adapter directory in every eval script. Reproducibility is the other gap: heavy_ab_eval_lora.py and compare_eval_results.py sample without a seed, so runs aren't repeatable and on a small eval set delta_pass_rate swings on just a few flipped examples — set a torch/transformers seed, reuse the seeded split, and with repeats>1 report the spread instead of a single mean. Finally, the max_seq_len=1024 in sft_lora.py truncates from the end, so any example longer than that loses the tail of its assistant reply, which is the training target itself; check your token-length distribution and raise it to 2048 if replies are being clipped.

- [ ] (example — delete me) Reply in the LOG with "inbox is live" and the current date, so I know the scheduled job works.

## LOG
inbox is live - 2026-06-25 10:08AM
<!-- the scheduled job appends dated results here -->
