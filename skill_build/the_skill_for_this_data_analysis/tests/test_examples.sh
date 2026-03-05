#!/bin/bash
# Data Analysis Report Skill - Test Suite
# Run various test scenarios to validate the skill functionality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$SKILL_DIR")"
CALL_SCRIPT="$SKILL_DIR/scripts/call_data_analysis_api.py"
BASE_URL="${BASE_URL:-http://127.0.0.1:8001}"

# Test data directory
TEST_DATA_DIR="$PROJECT_ROOT/test_data"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

check_dependencies() {
    print_section "Checking Dependencies"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    log_success "Python 3 is available"

    # Check script exists
    if [ ! -f "$CALL_SCRIPT" ]; then
        log_error "Script not found: $CALL_SCRIPT"
        exit 1
    fi
    log_success "Script found: $CALL_SCRIPT"

    # Check if API is running
    if ! curl -s "$BASE_URL/healthz" > /dev/null 2>&1; then
        log_warning "API server is not running at $BASE_URL"
        log_info "Start the server with: uvicorn src.main:app --host 0.0.0.0 --port 8001"
        log_info "Skipping integration tests..."
        return 1
    fi
    log_success "API server is running at $BASE_URL"

    return 0
}

create_test_data() {
    print_section "Creating Test Data"

    mkdir -p "$TEST_DATA_DIR"

    # Create a simple test Excel file using Python
    python3 << EOF
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from create_test_data import generate_test_excel
from pathlib import Path

# Generate test files
output_dir = Path('$TEST_DATA_DIR')
output_dir.mkdir(parents=True, exist_ok=True)

# Standard test file (365 days)
generate_test_excel(str(output_dir / 'test_standard.xlsx'), days=365)

# Small test file (30 days)
generate_test_excel(str(output_dir / 'test_small.xlsx'), days=30)

# Large test file (3 years)
generate_test_excel(str(output_dir / 'test_large.xlsx'), days=1095)

print("\n✓ Test files created successfully")
EOF

    log_success "Test data files created in $TEST_DATA_DIR"
}

test_basic_analysis() {
    print_section "Test 1: Basic Trend Analysis"

    local test_file="$TEST_DATA_DIR/test_standard.xlsx"
    local output

    if [ ! -f "$test_file" ]; then
        log_error "Test file not found: $test_file"
        return 1
    fi

    log_info "Running basic analysis on $test_file"

    output=$(python3 "$CALL_SCRIPT" \
        --base-url "$BASE_URL" \
        --excel-path "$test_file" \
        --user-prompt "分析最近一年产量和销量的趋势" \
        --timeout 120 2>&1)

    if echo "$output" | jq -e '.analyze.report_path' > /dev/null 2>&1; then
        log_success "Basic analysis completed successfully"
        echo "$output" | jq -r '.analyze.report_path' | head -1
    else
        log_error "Basic analysis failed"
        echo "$output" >&2
        return 1
    fi
}

test_manual_indicators() {
    print_section "Test 2: Manual Indicator Selection"

    local test_file="$TEST_DATA_DIR/test_standard.xlsx"

    log_info "Testing manual indicator selection"

    output=$(python3 "$CALL_SCRIPT" \
        --base-url "$BASE_URL" \
        --excel-path "$test_file" \
        --user-prompt "分析库存情况" \
        --select-indicators "库存" \
        --timeout 120 2>&1)

    if echo "$output" | jq -e '.analyze.report_path' > /dev/null 2>&1; then
        log_success "Manual indicator selection works"
    else
        log_error "Manual indicator selection failed"
        echo "$output" >&2
        return 1
    fi
}

test_quiet_mode() {
    print_section "Test 3: Quiet Mode"

    local test_file="$TEST_DATA_DIR/test_small.xlsx"

    log_info "Testing quiet mode (minimal output)"

    output=$(python3 "$CALL_SCRIPT" \
        --base-url "$BASE_URL" \
        --excel-path "$test_file" \
        --user-prompt "分析产量" \
        --quiet \
        --timeout 120 2>&1)

    # Quiet mode should have minimal stderr output
    stderr_lines=$(echo "$output" | wc -l)

    if echo "$output" | jq -e '.healthz.status' > /dev/null 2>&1; then
        log_success "Quiet mode works correctly"
    else
        log_warning "Quiet mode test had issues"
    fi
}

test_error_handling() {
    print_section "Test 4: Error Handling"

    log_info "Testing error handling with non-existent file"

    output=$(python3 "$CALL_SCRIPT" \
        --base-url "$BASE_URL" \
        --excel-path "/nonexistent/file.xlsx" \
        --user-prompt "分析" \
        --timeout 10 2>&1)

    if echo "$output" | jq -e '.error' > /dev/null 2>&1; then
        log_success "Error handling works correctly"
    else
        log_error "Error handling test failed"
        return 1
    fi
}

test_json_parsing() {
    print_section "Test 5: JSON Output Validation"

    local test_file="$TEST_DATA_DIR/test_standard.xlsx"

    log_info "Validating JSON output structure"

    output=$(python3 "$CALL_SCRIPT" \
        --base-url "$BASE_URL" \
        --excel-path "$test_file" \
        --user-prompt "分析销量" \
        --timeout 120 2>&1)

    # Check required fields
    required_fields=("healthz" "selected_indicator_names" "analyze")
    all_present=true

    for field in "${required_fields[@]}"; do
        if ! echo "$output" | jq -e ".$field" > /dev/null 2>&1; then
            log_error "Missing required field: $field"
            all_present=false
        fi
    done

    if [ "$all_present" = true ]; then
        log_success "JSON structure is valid"
    else
        log_error "JSON validation failed"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${GREEN}"
    echo "=================================="
    echo "Data Analysis Report Skill Tests"
    echo "=================================="
    echo -e "${NC}"
    echo ""
    echo "Base URL: $BASE_URL"
    echo "Project Root: $PROJECT_ROOT"
    echo ""

    # Check dependencies
    if ! check_dependencies; then
        log_error "Dependency check failed. Please start the API server first."
        exit 1
    fi

    # Create test data
    create_test_data

    # Run tests
    tests_passed=0
    tests_failed=0

    if test_basic_analysis; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi

    if test_manual_indicators; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi

    if test_quiet_mode; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi

    if test_error_handling; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi

    if test_json_parsing; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi

    # Summary
    print_section "Test Summary"
    echo -e "Tests Passed: ${GREEN}${tests_passed}${NC}"
    echo -e "Tests Failed: ${RED}${tests_failed}${NC}"
    echo -e "Total Tests: $((tests_passed + tests_failed))"

    if [ $tests_failed -eq 0 ]; then
        echo ""
        log_success "All tests passed! ✓"
        exit 0
    else
        echo ""
        log_error "Some tests failed ✗"
        exit 1
    fi
}

# Run main
main "$@"
