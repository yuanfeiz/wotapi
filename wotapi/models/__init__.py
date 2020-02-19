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
    Cancelling = 'k_cancelling'


class EventTopics:
    # indicates the start and end state of a task
    State = 'task_state'

    # the most detailed logs from script outputs
    Logs = 'task_logs'


class EventLogType(Enum):
    # Progress in percentage
    Progress = 'k_progress'

    # Raw logs
    Info = 'k_info'

    # Current results
    Results = 'k_results'

    # Schedule
    Schedule = 'k_schedule'