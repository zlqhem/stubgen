SHELL := /bin/bash

.DELETE_ON_ERROR:

.PHONY: all

all: test report

.PHONY: help
help:
	@echo
	@echo "Usage: make [TARGET]"
	@echo "--------------------------------------------------"
	@echo "List of targets"
	@echo
	@echo "   all 			- make everything (test, report)"
	@echo "   test			- compile the code and run unittest"
	@echo "   report 		- generate code analysis report"
	@echo "   clean 		- remove all generated files"
	@echo

# run unit tests
.PHONY: test
test:
	@py.test tests 

# generate report files
.PHONY: report
report:
	@py.test --cov-report term --cov src/ tests/

# remove all generated files
.PHONY: clean
clean:
	@git clean -fdx
