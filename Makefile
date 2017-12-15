.PHONY: all
all: desc.json pset.json

%.json: %.yml yamltojson.py
	python3 yamltojson.py $*
