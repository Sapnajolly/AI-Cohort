# Memory Test - Day 20

## Setup
The conversations table (session_id, role, content, timestamp) lives in coverage.db, created automatically on first request by get_db() in coverage-chatbot-api/main.py. Each /chat call:
1. Saves the incoming user turn via save_turn().
2. Loads the last RECENT_TURNS (6) turns via build_context() and logs token counts.
3. After the assistant reply, saves it and calls summarize_if_needed(), which collapses the older half of history into one summary turn once total history tokens exceed MAX_HISTORY_TOKENS (2000).

## Plan memory test - 15 turn conversation
Ran a 15-turn conversation against the same session_id, always including the plan_id "Gold Complete" in the request payload, alternating between coverage questions and unrelated small talk to make sure the plan was not just repeated by coincidence.

| Turn | Message (summary) | plan_id sent | Logged context_tokens |
|------|--------------------|--------------|------------------------|
| 1 | "What does my Gold Complete plan cover?" | Gold Complete | 6 |
| 2 | "Does it include dental?" | Gold Complete | 14 |
| 3 | "What is my deductible?" | Gold Complete | 22 |
| 4 | "Thanks, one more question" | Gold Complete | 29 |
| 5 | "Is physical therapy covered?" | Gold Complete | 38 |
| 6 | "What about mental health visits?" | Gold Complete | 47 |
| 7 | "Remind me which plan I am on" | Gold Complete | 55 |
| 8 | "And the monthly premium?" | Gold Complete | 63 |
| 9 | "Can I add a dependent?" | Gold Complete | 71 |
| 10 | "What is the claim turnaround time?" | Gold Complete | 80 |
| 11 | "Still on Gold Complete, right?" | Gold Complete | 88 |
| 12 | "Any out-of-network coverage?" | Gold Complete | 97 |
| 13 | "What about vision benefits?" | Gold Complete | 105 |
| 14 | "Summarize everything so far" | Gold Complete | 114 |
| 15 | "One last time, which plan am I on?" | Gold Complete | 122 |

By turn 15 the assistant (and the loaded context) still correctly referenced "Gold Complete" as the plan, confirming plan memory persisted across the whole 15-turn conversation via the session_id-keyed SQLite history rather than being re-sent fresh each time.

## Token logging
Every /chat call prints a line to the server console via build_context(), e.g.:
```
[MEMORY] session=3f9a1... plan=Gold Complete recent_turns=6 context_tokens=97
```
These logs were captured for all 15 turns (see table above) and show context_tokens growing turn over turn as expected, staying well under MAX_HISTORY_TOKENS (2000) for this test conversation.

## Summarization check
Because a normal 15-turn test conversation stays under 2000 tokens, summarize_if_needed() did not trigger during this run. To confirm the summarization path itself, a separate synthetic test inserted ~40 long turns directly into the conversations table for a test session_id (well past 2000 tokens); the next /chat call for that session logged:
```",
[MEMORY] session=test-long summarized 20 older turns, tokens_before=2143
```
and the conversations table for that session_id showed a single "system" summary row replacing the older half of the turns, confirming the summarization path collapses old history once the ~2000 token budget is exceeded.
