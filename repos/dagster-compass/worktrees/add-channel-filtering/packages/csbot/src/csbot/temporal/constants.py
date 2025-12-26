from enum import Enum

DEFAULT_TASK_QUEUE = "compass-queue"
DATASET_MONITORING_TASK_QUEUE = "dataset-monitoring"


class Workflow(Enum):
    DAILY_EXPLORATION_WORKFLOW_NAME = "daily_exploration"
    THREAD_HEALTH_INSPECTOR_WORKFLOW_NAME = "thread_health_inspector"
    DATASET_MONITORING_WORKFLOW_NAME = "dataset_monitor"
    DATASET_SYNC_WORKFLOW_NAME = "dataset_sync"
    ORG_ONBOARDING_CHECK_WORKFLOW_NAME = "org_onboarding_check"


class Activity(Enum):
    SEND_DAILY_EXPLORATION_ACTIVITY_NAME = "send_daily_exploration"
    INSPECT_THREAD_HEALTH_ACTIVITY_NAME = "inspect_thread_health"
    CREATE_BRANCH_ACTIVITY_NAME = "create_branch"
    SEND_NOTIFICATION_STARTED_ACTIVITY_NAME = "send_notification_started"
    PROCESS_DATASET_ACTIVITY_NAME = "process_dataset"
    FINALIZE_PULL_REQUEST_ACTIVITY_NAME = "finalize_pull_request"
    SEND_NOTIFICATION_COMPLETED_ACTIVITY_NAME = "send_notification_completed"
    SEND_SLACK_CONNECT_INVITE_ACTIVITY_NAME = "send_slack_connect_invite"
    LOG_ANALYTICS_ACTIVITY_NAME = "log_analytics"
    DATASET_MONITORING_ACTIVITY_NAME = "dataset_monitor"
    CONTEXT_STORE_LOADER_ACTIVITY_NAME = "context_store_loader"
    VALIDATE_ORG_ONBOARDING_ACTIVITY_NAME = "validate_org_onboarding"
