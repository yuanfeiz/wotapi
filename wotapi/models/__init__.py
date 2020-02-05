from enum import Enum


class ResultState(Enum):
    Positive = 'k_positive'
    Negative = 'k_negative'


class TaskState(Enum):
    Queued = 'k_queued'
    Ongoing = 'k_ongoing'
    Completed = 'k_completed'
    Failed = 'k_failed'
    Cancelled = 'k_cancelled'


class EventTopics:
    State = 'task_state'
    Logs = 'task_logs'


class EventLogType:
    Progress = 'k_progress'
    Info = 'k_info'