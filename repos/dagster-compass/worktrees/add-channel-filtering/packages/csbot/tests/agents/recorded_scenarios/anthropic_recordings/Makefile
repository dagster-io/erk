# Makefile for recorded scenarios testing
# Provides convenient shortcuts for compass-dev agent-record commands

# Check for required environment variables
check-env:
	@if [ -z "$(ANTHROPIC_API_KEY)" ]; then \
		echo "❌ Error: ANTHROPIC_API_KEY environment variable is required"; \
		echo "   Set it with: export ANTHROPIC_API_KEY=your-key-here"; \
		exit 1; \
	fi

# Recording commands - record all scenarios
record-all: check-env
	@echo "🎬 Recording all scenarios..."
	compass-dev agent-record record --all

# Validation and testing commands
check-all:
	@echo "🧪 Checking all recordings..."
	compass-dev agent-record check --verbose

test:
	@echo "🧪 Running pytest tests..."
	pytest test_recorded_responses.py -v

# Utility commands
list:
	@echo "📁 Listing available recordings..."
	compass-dev agent-record list

clean:
	@echo "🧹 Removing all recordings..."
	rm -rf recordings/text_responses/*.json
	rm -rf recordings/tool_calling/*.json
	rm -rf recordings/error_cases/*.json
	rm -rf recordings/edge_cases/*.json
	@echo "✅ Recordings cleaned"

# Default target
.DEFAULT_GOAL := list
.PHONY: check-env record-all check-all test list clean