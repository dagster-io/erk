---
columns:
  - AI_MODEL (VARCHAR(16777216))
  - AI_RESPONSE (VARCHAR(16777216))
  - BEST_DOC_RELEVANCE (FLOAT)
  - DISCUSSIONS_FOUND (NUMBER(38,0))
  - DOCS_FOUND (NUMBER(38,0))
  - INPUT_TOKENS (NUMBER(38,5))
  - ISSUES_FOUND (NUMBER(38,0))
  - IS_VALID_QUESTION (BOOLEAN)
  - OUTPUT_TOKENS (NUMBER(38,5))
  - QUESTION_ORDER_IN_SESSION (NUMBER(18,0))
  - RESPONSE_GENERATION_COST (FLOAT)
  - RESPONSE_TIME_MS (NUMBER(38,5))
  - SEARCH_RESULTS_SUMMARY (OBJECT)
  - SESSION_ID (VARCHAR(16777216))
  - TIMESTAMP_END (TIMESTAMP_NTZ(9))
  - TIMESTAMP_START (TIMESTAMP_NTZ(9))
  - TOTAL_QUESTIONS_IN_SESSION (NUMBER(18,0))
  - TOTAL_WORKFLOW_COST (FLOAT)
  - TOTAL_WORKFLOW_TIME (NUMBER(38,0))
  - USER_QUESTION (VARCHAR(16777216))
  - VALIDATION_REASON (VARCHAR(16777216))
  - WORKFLOW_DISPLAY_NAME (VARCHAR(16777216))
  - WORKFLOW_ID (VARCHAR(16777216))
  - WORKFLOW_RUN_ID (VARCHAR(16777216))
  - WORKFLOW_TYPE (VARCHAR(5))
schema_hash: 8be6e29d01aa70d7ba940abce46adf8dea1d1321de656553575921fe3e9513bd
---

# Scout Run Logs Dataset Summary

## Overall Dataset Characteristics

- **Total Rows**: 36,541 workflow execution records
- **Data Quality**: High quality with minimal null values (most columns have 0-3% null rates)
- **Time Period**: Data spans from June 2025 to September 2025
- **Primary Purpose**: Comprehensive logging of Scout AskAI workflow executions across different interfaces (web, Slack, other) with detailed performance metrics and search results

**Table Comment**: Comprehensive Scout AskAI workflow execution logs with parsed conversation data, performance metrics, and search results. This table combines data from different workflow types (web, Slack, other) to provide a unified view of AI assistant interactions, validation results, and search quality metrics for analytics and monitoring.

## Column Details

### Identifiers & Workflow Context

- **WORKFLOW_DISPLAY_NAME**: Human-readable workflow names (10 unique values including "Dagster Copilot Docs", "BDR Email Generator", "CISObot AskAI Copilot")
- **SESSION_ID**: Groups related workflow executions (18,096 unique sessions)
- **WORKFLOW_ID**: Template identifiers (10 unique workflow types)
- **WORKFLOW_RUN_ID**: Unique execution identifier (36,541 unique values - one per row)

### Timing & Performance Metrics

- **TIMESTAMP_START/END**: Precise execution timestamps with nanosecond precision
- **TOTAL_WORKFLOW_TIME**: Execution duration in milliseconds (range: 549ms to 824,141ms)
- **RESPONSE_TIME_MS**: AI response generation time (range: 0ms to 630,017ms, 0.25% nulls)

### Cost & Resource Usage

- **TOTAL_WORKFLOW_COST**: Complete workflow cost (range: $0.00 to $0.68)
- **RESPONSE_GENERATION_COST**: AI-specific costs (range: $0.003 to $0.678, 2.53% nulls)
- **INPUT_TOKENS/OUTPUT_TOKENS**: Token usage metrics for AI models

### Conversation Context

- **QUESTION_ORDER_IN_SESSION**: Sequential question numbering (1-124)
- **TOTAL_QUESTIONS_IN_SESSION**: Session question count (1-124 total questions)
- **USER_QUESTION**: User input text (0.22% nulls, 36,042 unique questions)
- **AI_RESPONSE**: AI-generated responses (2.53% nulls, 35,615 unique responses)

### Quality & Validation

- **IS_VALID_QUESTION**: Boolean validation status (17.81% nulls)
- **VALIDATION_REASON**: Validation explanations (17,177 unique reasons)
- **AI_MODEL**: Model used (5 models: claude-opus-4-1, claude-sonnet-4-0, gemini-2.0-flash, gpt-4.1, gpt-4o)

### Search Results & Relevance

- **BEST_DOC_RELEVANCE**: Document similarity scores (0.11 to 1.0, 6.17% nulls)
- **DOCS_FOUND**: Documentation results count (0-10)
- **ISSUES_FOUND**: GitHub issues found (0-10)
- **DISCUSSIONS_FOUND**: Discussion results count (0-10)
- **SEARCH_RESULTS_SUMMARY**: JSON object with detailed search results (36,065 unique summaries)

### Workflow Classification

- **WORKFLOW_TYPE**: Interface type (web, slack, other - 3 distinct values)

## Query Considerations

### Good for Filtering

- **WORKFLOW_DISPLAY_NAME**: Filter by specific AI assistants/tools
- **WORKFLOW_TYPE**: Filter by interface (web vs Slack vs other)
- **AI_MODEL**: Filter by specific AI model used
- **IS_VALID_QUESTION**: Filter validated vs non-validated questions
- **TIMESTAMP_START/END**: Time-based filtering for trends
- **DOCS_FOUND/ISSUES_FOUND/DISCUSSIONS_FOUND**: Filter by search result availability

### Good for Grouping/Aggregation

- **WORKFLOW_DISPLAY_NAME**: Analyze performance by workflow type
- **AI_MODEL**: Compare model performance and costs
- **WORKFLOW_TYPE**: Interface usage patterns
- **QUESTION_ORDER_IN_SESSION**: Analyze conversation flow patterns
- **SESSION_ID**: Session-level analytics

### Potential Join Keys

- **SESSION_ID**: Link related questions in same conversation
- **WORKFLOW_ID**: Connect to workflow configuration data
- **WORKFLOW_RUN_ID**: Unique execution identifier for detailed analysis

### Data Quality Considerations

- **Null Handling**: Most AI-related metrics have ~2.5% nulls (likely failed executions)
- **Validation Data**: 17.81% of records lack validation data
- **Search Relevance**: 6.17% missing best document relevance scores
- **Token Metrics**: Available for 97.47% of records with AI responses
- **Cost Data**: Comprehensive cost tracking with minimal missing data

### Performance Patterns

- **High Variability**: Response times range from milliseconds to over 10 minutes
- **Token Usage**: Input tokens vary dramatically (250 to 158,261)
- **Search Results**: Most queries return full result sets (10 docs/issues)
- **Session Patterns**: Sessions range from single questions to extensive 124-question conversations

## Keywords

Scout, AskAI, Dagster, workflow execution, AI assistant, conversation logs, performance metrics, search results, token usage, response time, validation, Claude, GPT, web interface, Slack integration, document retrieval, GitHub issues, cost tracking, session analysis

## Table and Column Documentation

**Table Comment**: Comprehensive Scout AskAI workflow execution logs with parsed conversation data, performance metrics, and search results. This table combines data from different workflow types (web, Slack, other) to provide a unified view of AI assistant interactions, validation results, and search quality metrics for analytics and monitoring.

**Column Comments**:

- WORKFLOW_DISPLAY_NAME: Human-readable name of the Scout workflow
- SESSION_ID: Session identifier grouping related workflow executions
- WORKFLOW_ID: Identifier for the workflow type/template
- WORKFLOW_RUN_ID: Unique identifier for this specific workflow execution
- TOTAL_WORKFLOW_COST: Total cost for the entire workflow execution
- TIMESTAMP_START: When the workflow execution started
- TOTAL_WORKFLOW_TIME: Total elapsed time for the workflow execution in milliseconds
- TIMESTAMP_END: When the workflow execution ended
- QUESTION_ORDER_IN_SESSION: Order of this question within the session (1st, 2nd, etc.)
- TOTAL_QUESTIONS_IN_SESSION: Total number of questions asked in this session
- USER_QUESTION: The user's question or input to the AI assistant
- AI_RESPONSE: The AI assistant's response to the user's question
- IS_VALID_QUESTION: Boolean indicating whether the user's question was considered valid by the validation system
- VALIDATION_REASON: Short explanation of why the question was or wasn't valid
- AI_MODEL: The specific AI model used to generate the response
- RESPONSE_GENERATION_COST: Cost specifically for AI response generation
- INPUT_TOKENS: Number of input tokens used in the AI model
- RESPONSE_TIME_MS: Time taken to generate the AI response in milliseconds
- OUTPUT_TOKENS: Number of output tokens generated by the AI model
- BEST_DOC_RELEVANCE: Relevance score of the best matching document found (similarity score or vector distance)
- DOCS_FOUND: Number of relevant documents found in the search
- ISSUES_FOUND: Number of relevant GitHub issues found in the search
- DISCUSSIONS_FOUND: Number of relevant discussions found in the search
- WORKFLOW_TYPE: Type of workflow interface (web, slack, other)
- SEARCH_RESULTS_SUMMARY: JSON object containing condensed search results with top documents, issues, and discussions for detailed analysis
