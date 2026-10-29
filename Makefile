.PHONY: check doctor demo
check:
	python3 -m unittest discover -s tests -v
	python3 -m harness validate
doctor:
	python3 -m harness doctor
demo:
	python3 -m harness demo --port 8765
