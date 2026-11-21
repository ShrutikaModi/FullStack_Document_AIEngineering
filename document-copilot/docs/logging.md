# Logging: what the backend writes and how to use it

Every log line is a set of named fields (not a sentence), so one question can be found by its
ids and slow or failed turns can be counted. Setup is in `backend/app/log_setup.py`; the format
is chosen by `LOG_FORMAT` (`console` locally, `json` on Railway).

## One turn, as printed locally

Values from a real run (field order and colours differ on screen):

```text
turn_started    request_id=5d65cc39-… thread_id=0cdec591-… user_id=a238bcd8-… question_chars=47 history=0
model_response  ms=2536 input_tokens=2054 output_tokens=51
tool_call       tool=search_filings tickers=['AAPL'] fiscal_years=[2024] section='Item 7'
                query='iPhone revenue' reason="Find Apple's iPhone revenue in fiscal 2024" results=8 ms=3280
model_response  ms=1650 input_tokens=6362 output_tokens=55
turn_finished   outcome=answered ms=8486 searches=1 sources=1
```

(Every line also carries `request_id`, `thread_id` and `user_id`; they are shown once above to
keep it short. Each line also has `timestamp` and `level`.)

The same search line in production (`LOG_FORMAT=json`):

```json
{"tool": "search_filings", "tickers": ["AAPL"], "fiscal_years": [2024], "section": "Item 7", "query": "iPhone revenue", "reason": "Find Apple's iPhone revenue in fiscal 2024", "results": 8, "ms": 3280, "request_id": "5d65cc39-…", "thread_id": "0cdec591-…", "user_id": "a238bcd8-…", "event": "tool_call", "level": "info", "timestamp": "2026-11-21T15:31:30.971204Z"}
```

## The lines

| Event | When | Useful fields |
| ----- | ---- | ------------- |
| `turn_started` | A question arrives | `question_chars`, `history` (earlier messages sent to the model) |
| `model_response` | The model answered one step (a search request, or the final answer) | `ms`, `input_tokens`, `output_tokens` |
| `tool_call` | A search ran (or was refused at the limit) | `query`, `tickers`, `fiscal_years`, `section`, `results`, `ms`, `refused` |
| `citation_retry` | The answer broke a citation rule and the model is asked to fix it (each one is a whole extra model call) | `problems`: the rule text |
| `blocked by content filter` | Azure refused the question | `filters` |
| `grounding failed`, `model call failed`, `agent run failed`, `could not save chat turn` | A failure, with a traceback | |
| `turn_finished` | The turn is over, whatever happened | `outcome`, `ms`, `searches`, `sources` |

`outcome` is one of: `answered`, `grounding_failed`, `content_blocked`, `model_unavailable`,
`search_failed`, `save_failed`, `client_disconnected` (the browser went away mid-answer).

`request_id` is the id of the assistant message the turn produces, so a log line can be matched
to the saved message and to the `messageId` the browser received.

## Privacy

The question and the answer are never logged, only the question's length. `user_id` is the
account id, never the email. Note that `query` and `reason` are the model's own wording for the
search and may echo part of the question.

## How to use it

- **"My question failed at 3pm."** Find lines with that `user_id` around that time, take the
  `request_id` from the `turn_finished` line, and read all lines with that `request_id` in order.
  `outcome` says how it ended; the line before it says where it went wrong.
- **Why was it slow?** Compare `ms` on `model_response` lines (model time) with `ms` on
  `tool_call` lines (search time); `turn_finished.ms` is the total.
- **Which citation rule does the model break?** Search for `citation_retry` and read `problems`.
- **Cost of a question.** Add up `input_tokens` and `output_tokens` over its `model_response` lines.
