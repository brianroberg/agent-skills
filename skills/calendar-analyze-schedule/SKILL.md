---
name: calendar-analyze-schedule
description: Analyze schedule patterns and workload
allowed-tools: Bash
---

# Analyze Schedule

Get AI-powered analysis of your schedule patterns and workload. This is a **read-only**
operation that provides insights without modifying your calendar.

## Prerequisites

Requires `CALENDAR_AGENT_URL` environment variable to be set.

## Usage

When this skill is invoked, run:

```bash
curl -s -X POST "$CALENDAR_AGENT_URL/analyze-schedule" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "primary",
        "time_min": "START_ISO",
        "time_max": "END_ISO",
        "analysis_type": "ANALYSIS_TYPE"
    }' \
    | jq .
```

## Analysis Types

| Type | Description |
|------|-------------|
| `overview` | General summary of the schedule |
| `workload` | Meeting load analysis (hours per day, back-to-backs) |
| `patterns` | Recurring patterns and habits |
| `conflicts` | Overlapping events and scheduling issues |

## Request Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `calendar_id` | No | `primary` | Calendar to analyze |
| `time_min` | Yes | - | Start of analysis range (ISO 8601) |
| `time_max` | Yes | - | End of analysis range (ISO 8601) |
| `analysis_type` | No | `overview` | Type of analysis to perform |

## Examples

**Get overview for this week:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/analyze-schedule" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "primary",
        "time_min": "2026-01-27T00:00:00-05:00",
        "time_max": "2026-01-31T23:59:59-05:00",
        "analysis_type": "overview"
    }' \
    | jq .
```

**Analyze workload for the month:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/analyze-schedule" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "primary",
        "time_min": "2026-01-01T00:00:00-05:00",
        "time_max": "2026-01-31T23:59:59-05:00",
        "analysis_type": "workload"
    }' \
    | jq .
```

**Find scheduling conflicts:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/analyze-schedule" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "primary",
        "time_min": "2026-01-27T00:00:00-05:00",
        "time_max": "2026-02-07T23:59:59-05:00",
        "analysis_type": "conflicts"
    }' \
    | jq .
```

**Identify recurring patterns:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/analyze-schedule" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "primary",
        "time_min": "2026-01-01T00:00:00-05:00",
        "time_max": "2026-01-31T23:59:59-05:00",
        "analysis_type": "patterns"
    }' \
    | jq .
```

## Response Format

The response includes the analysis results:

```json
{
  "success": true,
  "analysis_type": "workload",
  "period": {
    "start": "2026-01-27",
    "end": "2026-01-31"
  },
  "analysis": {
    "total_meetings": 15,
    "total_hours": 12.5,
    "avg_per_day": 2.5,
    "busiest_day": "Wednesday",
    "back_to_back_count": 3,
    "insights": [
      "You have 3 back-to-back meeting blocks this week",
      "Wednesday is your busiest day with 4 hours of meetings",
      "Friday afternoon is relatively free for focus work"
    ]
  }
}
```

## Use Cases

- "How busy is my week looking?"
- "Do I have any scheduling conflicts?"
- "What are my meeting patterns this month?"
- "Am I spending too much time in meetings?"
