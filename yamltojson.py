import json
import sys
import yaml

with open(sys.argv[1] + '.yml') as yaml_file:
    with open(sys.argv[1] + '.json', 'w') as json_file:
        json.dump(yaml.safe_load(yaml_file), json_file, indent=2,
                  sort_keys=True)
        json_file.write('\n')
