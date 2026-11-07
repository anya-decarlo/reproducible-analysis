PY := python3

.PHONY: all ingest transform analyze validate verify test clean

all: ingest transform analyze validate verify

ingest:
	$(PY) -m pipeline.ingest

transform:
	$(PY) -m pipeline.transform

analyze:
	$(PY) -m pipeline.analyze

validate:
	$(PY) -m pipeline.validate

verify:
	$(PY) -m pipeline.verify

test:
	$(PY) -m unittest discover -s tests

clean:
	rm -f outputs/*.csv outputs/validation_report.json build/run.json
