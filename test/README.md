# Agent Hub - Test Suite

## Overview

This directory contains comprehensive unit and integration tests for the Agent Hub project, covering all Python scripts in `scripts/`.

## Test Files

| File | Description | Tests Coverage |
|------|-------------|----------------|
| `conftest.py` | Shared fixtures and test configuration | HubFixture, tmp_project_dir, mock_catalog |
| `test_build_catalog.py` | Unit tests for catalog building | Frontmatter parsing, metadata inference, entry building |
| `test_detect_project.py` | Unit tests for project detection | Signal extraction, stack scoring, main function |
| `test_publish.py` | Unit tests for publishing skills | Publish flow, conflict detection, manifest creation |
| `test_import_skill.py` | Unit tests for skill import | Import logic, file operations, frontmatter validation |
| `test_validate.py` | Unit tests for library validation | All 9 validation checks |
| `test_integration.py` | System integration tests | End-to-end workflows across modules |

## Running Tests

```bash
# Run all tests with verbose output
pytest test/ -v --tb=short

# Run specific test file
pytest test/test_build_catalog.py -v

# Run specific test class
pytest test/test_publish.py::TestPublishOne -v

# Run with coverage (requires pytest-cov)
pytest test/ --cov=scripts --cov-report=html

# Run only tests matching pattern
pytest test/ -k "catalog"  # All catalog-related tests
```

## Test Fixtures

### HubFixture
Complete isolated fake Agent Hub for testing. Provides:
- Source project (superpowers/) with skills and agents
- Library directory (agent-hub-index/library/) with full structure
- Pre-built collections and stacks
- Methods to build catalog, modify skills, create projects

```python
def test_example(hub):
    # Create a new project
    project = hub.make_project("myproject")
    
    # Get the current catalog
    catalog = hub.get_catalog()
    
    # Publish skills to project
    publish_one("test-skill", catalog, project, ...)
```

## Test Categories

### Unit Tests
- Single function/method testing
- Input/output verification
- Edge case handling
- Error conditions

### Integration Tests
- Multi-module workflows
- Cross-script data flow
- End-to-end scenarios
- Command-line execution

## Coverage Summary

| Script | Unit Tests | Integration Tests | Total |
|--------|------------|-------------------|-------|
| build-catalog.py | 25+ | 3 | 28+ |
| detect-project.py | 18+ | 4 | 22+ |
| publish-to-project.py | 20+ | 5 | 25+ |
| import-skill.py | 15+ | 2 | 17+ |
| validate.py | 30+ | 3 | 33+ |

## Adding New Tests

```python
# In test_<script_name>.py

class TestNewFeature:
    def test_scenario(self, hub):
        """Test a new feature using existing fixtures."""
        # Arrange
        project = hub.make_project("test-project")
        
        # Act
        result = some_function(...)
        
        # Assert
        assert result == expected_value
```

## Test Data Files

The test suite uses:
- `library/catalog.json` - Read-only reference catalog
- `hub.root / "superpowers/"` - Fake source project (generated per-test)