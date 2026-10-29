.PHONY: check doctor demo
check:
	python3 -m unittest discover -s tests -v
	python3 -m harness validate
	python3 -m harness plan-check examples/task-plan.json
	python3 -m unittest discover -s examples/bugfix/solution -v
doctor:
	python3 -m harness doctor
demo:
	python3 -m harness demo --port 8765
