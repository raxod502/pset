.PHONY: all
all: pset.json

pset.json: pset.yml yamltojson.py
	python3 yamltojson.py pset
