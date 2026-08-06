# ChatGPT User Collaboration Style

## Prompt delivery preference

When the user asks ChatGPT to prepare a prompt for another AI agent, use a two-layer delivery by default.

### Layer 1: detailed Markdown handoff

Put all long-form context and execution details into a Markdown file inside the relevant project directory. The detailed Markdown should normally contain:

- absolute workspace/worktree paths;
- expected branch and Python/runtime paths;
- required reading, using absolute paths where possible;
- current audit verdict and blockers;
- exact findings and remediation requirements;
- scope boundaries and prohibited operations;
- RED-to-GREEN testing requirements;
- exact validation commands;
- required reports and structured evidence;
- completion criteria and final status lines.

The detailed file should be self-contained so an AI in a new window with no prior conversation memory can execute it safely.

### Layer 2: short copy-paste prompt

In chat, do not repeat the full document. Return a concise prompt that the user can paste directly into another AI window. It should normally contain only:

1. the absolute path of the Markdown file that must be read completely;
2. a one- or two-sentence task objective;
3. the most important scope restrictions, such as no commit/push/merge, no dependency installation, and preservation of inherited dirty files;
4. the required deliverable or terminal status;
5. an instruction to stop and report blockers honestly rather than fabricating PASS.

The short prompt should generally stay within roughly 5–15 lines unless the user explicitly asks for more detail in chat.

## Default behavior

- If the user says “写一份提示词”, first write the detailed Markdown file, then provide its absolute path and the short copy-paste prompt.
- Apply the same two-layer rule to long audits, remediation findings, handoffs, designs, plans, and execution specifications: save the complete material in a versioned Markdown file, then keep the chat response short.
- Do not place a long audit or remediation specification directly in chat unless the user explicitly asks to see the full text in chat.
- When the likely next action is to send the work to another AI, always include one fenced, immediately copyable prompt block; do not make the user rewrite or assemble the prompt themselves.
- If the user says they are opening a new AI window, assume that AI has no previous memory and make the Markdown self-contained.
- If the user provides a target directory, place the detailed Markdown there unless doing so would overwrite an existing audit artifact.
- Prefer a new round/versioned filename instead of overwriting prior submissions or remediation prompts.
- Keep audit findings, evidence requirements, and safety constraints in the Markdown rather than flooding the chat response.
- The chat response should lead with the completed Markdown path, followed by the copy-paste block.

## Concise chat contract

By default, the user-facing chat response should contain only:

1. one-line outcome or status;
2. the clickable Markdown path and its absolute path;
3. a short copy-paste prompt when another AI is expected to act;
4. at most a few essential warnings that cannot safely be deferred to the Markdown.

The user strongly prefers “直接粘贴”: the fenced prompt must be self-contained at the routing level, explicitly tell the next AI to read the referenced Markdown completely, and avoid duplicating the long instructions already stored there.
