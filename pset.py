#!/usr/bin/env python3

import json
import os
import re
import sys

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    class yaml:
        def __getattr__(self, name):
            return None
    YAML_AVAILABLE = False

"""List of possible base filenames for pset configuration files."""
CONFIG_ROOTS = [".pset", "pset"]

"""List of possible file extensions for JSON files."""
JSON_EXTENSIONS = ["json"]

"""List of possible file extensions for YAML files."""
YAML_EXTENSIONS = ["yml", "yaml"]

"""List of possible file extensions for pset configuration files."""
CONFIG_EXTENSIONS = JSON_EXTENSIONS + YAML_EXTENSIONS

def path_is_root(path):
    """Check if a path resolves to the root of the filesystem."""
    canonical = os.path.realpath(path)
    return canonical == os.path.dirname(canonical)

def repository_file(filename):
    """Return the absolute path to a file in the pset repository.

    The pset repository is the directory containing pset.py, and
    filename is resolved relative to this directory.
    """
    this_file = os.path.realpath(__file__)
    this_dir = os.path.dirname(this_file)
    return os.path.join(this_dir, filename)

def print_stderr(*args, **kwargs):
    """Print a message to stderr.

    args and kwargs are passed to the print function.
    """
    return print(*args, file=sys.stderr, **kwargs)

def parse_json(filename):
    """Parse a JSON file and return the parsed object."""
    with open(filename) as f:
        return json.load(f)

def parse_yaml(filename):
    """Parse a YAML file and return the parsed object."""
    with open(filename) as f:
        return yaml.safe_load(f)

class ConfigConversionError(Exception):
    """Error thrown when configuration value is unusably malformed."""
    pass

class Config:
    """Configuration parsing and validation engine."""

    def __init__(self):
        """Parse and validate configuration.

        After construction, configuration data may be queried
        immediately.
        """
        self.read_config_descriptions()
        self.read_default_config()
        self.read_user_config()
        self.read_command_line_arguments()

    def read_config_descriptions(self):
        """Read and store configuration schema description from desc.json.

        The schema is not validated. Loading an invalid schema results
        in undefined behavior.
        """
        self.config_keys = parse_json(repository_file("desc.json"))

    def read_default_config(self):
        """Read and store default configuration.

        If the default configuration file is unavailable or malformed,
        throw an error.
        """
        default_config_file = repository_file("pset.json")
        try:
            self.warn_fatal = True
            self.default_config = self.load_config_file(default_config_file)
        finally:
            del self.warn_fatal

    def read_user_config(self):
        try:
            self.warn_fatal = False
            self.user_configs = []
            cur_dir = os.getcwd()
            while True:
                cur_dir = os.path.realpath(cur_dir)
                filenames = sorted(os.listdir(cur_dir))
                for filename in filenames:
                    for root in CONFIG_ROOTS:
                        for ext in CONFIG_EXTENSIONS:
                            if filename == root + "." + ext:
                                path = os.path.join(cur_dir, filename)
                                self.user_configs.append(
                                    (path, self.load_config_file(path)))
                if path_is_root(cur_dir):
                    break
                cur_dir = os.path.split(cur_dir)[0]
        finally:
            del self.warn_fatal

    def load_config_file(self, filename):
        """Load a configuration file and return the data.

        If the file is unavailable or malformed, signal this using the
        warn function. If the warn function does not throw an error,
        make an effort to extract as much useful data as possible from
        malformed configuration file.
        """
        try:
            ext = os.path.splitext(filename)[1]
            if ext in YAML_EXTENSIONS:
                if YAML_AVAILABLE:
                    config = parse_yaml(filename)
                else:
                    self.warn("Ignoring '{}' because PyYAML is not available"
                              .format(filename))
                    return {}
            elif ext in JSON_EXTENSIONS:
                config = parse_json(filename)
            else:
                raise AssertionError("Unexpected file extension for file '{}'"
                                     .format(filename))
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            self.warn("Ignoring '{}' because it is malformed: {}"
                      .format(filename, e.message))
            return {}
        if not isinstance(config, dict):
            self.warn("Ignoring '{}' because it is not a map: {}"
                      .format(filename, repr(config)))
            return {}
        for key in config.values():
            if key not in self.config_keys:
                self.warn("Ignoring unknown key '{}' from '{}'"
                          .format(key, filename))
                del config[key]
        return config

    def warn(self, msg):
        """Signal a configuration parsing or validation warning.

        If warn_fatal is true, throw an error. Otherwise, print the
        message to stderr.
        """
        if self.warn_fatal:
            raise AssertionError(
                "Got warning while loading default config file: {}"
                .format(msg))
        print_stderr(msg)

    def read_command_line_arguments(self):
        """Read and store configuration from the command-line arguments.

        The syntax is as follows. You may assign a value to an
        arbitrary key in the configuration map, and this value can be
        a string, list of strings, or map of strings. (Integers,
        booleans, and so on are interpreted from strings.)

        The syntax '--foo bar' will assign the string "bar" to the key
        "foo". The syntax '--foo bar baz quux' will assign the list
        ["bar", "baz", "quux"] to the key "foo". The syntax '--foo
        bar=baz quux=flarble' will assign the map {"bar": "baz",
        "quux": "flarble"} to the key "foo".

        To be precise, an argument beginning with '--' signals a key,
        and all arguments until the next one beginning with '--' are
        values. All arguments before the first one beginning with '--'
        are ignored, with a warning. Whether a sequence of values is a
        list or map is determined by whether the first value contains
        an equals sign. In a list, all values containing equals signs
        are ignored, with a warning. In a map, all values not
        containing equals signs are ignored, with a warning. In a map,
        the values are separated into key and value by partitioning at
        the first equals sign. If no values are specified, the value
        is set to None.
        """
        self.cl_config = {}
        args = sys.argv[1:]
        key = None
        values = []
        for arg in args + [None]:
            if arg.startswith("--") or arg is None:
                if len(values) >= 2:
                    is_map = None
                    for value in values:
                        if is_map not in (None, "=" in value):
                            self.warn(
                                "Ignoring command-line setting of key '{}' "
                                .format(key) +
                                "due to inconsistent args '{}' and '{}'"
                                .format(values[0], value))
                            is_map = None
                            break
                        is_map = "=" in value
                    if is_map:
                        value_map = {}
                        for value in values:
                            subkey, val = (re.match(r"^(.*?)=(.*)$", value)
                                           .groups()[1:3])
                            value_map[subkey] = val
                        self.cl_config[key] = value_map
                elif len(values) == 1:
                    self.cl_config[key] = values[0]
                else:
                    self.cl_config[key] = None
                if arg is None:
                    break
                key = arg[2:]
                values = []
            elif key is None:
                self.warn("Ignoring arg '{}' with no key specified"
                          .format(arg))
            else:
                values.append(arg)
        for key in self.cl_config.values():
            if key not in self.config_keys:
                self.warn(
                    "Ignoring unknown key '{}' from command-line arguments"
                    .format(key))
                del self.cl_config[key]

    def get_boolean(self, key):
        def convert(val, context):
            if val in [True, False, None]:
                return val
            elif str(val).lower() in ["y", "yes", "true", "on", "1"]:
                return True
            elif str(val).upper() in ["n", "no", "false", "off", "0"]:
                return False
            else:
                raise ConfigConversionError(
                    "must be y/n, yes/no, true/false, on/off, or 0/1")
        return self.get(key, convert)

    def get_string(self, key):
        def convert(val, context):
            return str(val)
        return self.get(key, convert)

    def get_length(self, key):
        # For now.
        return self.get_string(key)

    def get_enum(self, key, allowed_values):
        def convert(val, context):
            val = str(val)
            if val in allowed_values:
                return val
            else:
                raise ConfigConversionError(
                    "must be one of: " + ", ".join(allowed_values))
        return self.get(key, convert)

    def get_string_list(self, key):
        def convert(vals, context):
            return [str(val) for val in vals]
        return self.get(key, convert)

    def get_enum_list(self, key, allowed_values, unique=False):
        def convert(vals, context):
            if not isinstance(vals, list):
                raise ConfigConversionError("must be list")
            result = []
            seen = set()
            for val in vals:
                val = str(val)
                if unique and val in seen:
                    self.warn(
                        "ignoring duplicate value '{}' for key '{}'"
                        .format(val, key) + context)
                elif val in allowed_values:
                    result.append(val)
                    seen.add(val)
                else:
                    self.warn(
                        "ignoring invalid value '{}' for key '{}': "
                        "must be one of: " + ", ".join(allowed_values))
            return result
        return self.get(key, convert)

    def get_enum_enum_map(self, key, allowed_keys, allowed_values):
        def convert(kv_map, context):
            if not isinstance(kv_map, dict):
                raise ConfigConversionError("must be map")
            result = {}
            for key, val in kv_map.items():
                key = str(key)
                val = str(val)
                if key in result:
                    self.warn(
                        "ignoring extra value '{}' for key '{}'"
                        .format(val, key) + context)
                elif key not in allowed_keys:
                    self.warn(
                        "ignoring value '{}' for invalid key '{}': key "
                        "key must be one of: ".format(val, key) +
                        ", ".join(allowed_keys))
                elif val not in allowed_values:
                    self.warn(
                        "ignoring invalid value '{}' for key '{}': key "
                        "value must be one of: ".format(val, key) +
                        ", ".join(allowed_values))
                else:
                    result[key] = val
            return result
        return self.get(key, convert)

    def get(self, key, convert):
        sources = [
            (self.cl_config, " from command-line arguments", False),
            *((cfg, " from '{}'".format(fname), False)
              for cfg, fname in self.user_configs),
            (self.default_config, " from default config", True)
        ]
        try:
            for config, context, warn_fatal in sources:
                self.warn_fatal = warn_fatal
                if key in config:
                    try:
                        return convert(config[key], context)
                    except ConfigConversionError as e:
                        self.warn("ignoring invalid value '{}' for key '{}'"
                                  .format(config[key], key) + context + ": " +
                                  e.message)
        finally:
            del self.warn_fatal

def generate_macro_args():
    args = []
    for i in range(1, 10):
        args.append("#" + str(i))
    return args

MACRO_ARGS = generate_macro_args()

def generate_list_styles():
    formats = [
        "({})", "{})", "{}.",
    ]
    macros = {
        "a": r"\alph*",
        "A": r"\Alph*",
        "i": r"\roman*",
        "I": r"\Roman*",
        "1": r"\arabic*",
    }
    list_styles = {}
    for format in formats:
        for key, macro in macros.items():
            list_styles[format.format(key)] = format.format(macro)
    return list_styles

LIST_STYLES = generate_list_styles()

VARIABLES = ["name", "assignment", "class", "duedate"]
IFS = ["clearpage"]
MACROS = ["problem", "solution", "maybeclearpage"]

MARGINALS = VARIABLES + ["pagenumber"]
MARGINAL_POSITIONS = [
    "lhead", "chead", "rhead", "lfoot", "cfoot", "rfoot"
]

def sort_by(items, order):
    def sort_key(item):
        try:
            return [order.index(item), item]
        except ValueError:
            return [len(order), item]
    return sorted(items, key=sort_key)

def combine_block(*commands):
    return "\n".join(commands)

def combine_blocks(*groups):
    combined = []
    for i, group in groups:
        if i != 0:
            combined.append("")
        combined.extend(group)
    return combined

def format_marginal(content, variables):
    if content in VARIABLES:
        variables.add(content)
        return r"\{}".format(content)
    elif content == "pagenumber":
        return r"\thepage{} of \pageref{LastPage}"
    else:
        raise AssertionError("Unknown content key: " + content)

def format_problem(config, problem, *args):
    return [r"\section*{{{}}}".format(problem)], 1

def format_solution(config, *args):
    return [r"\hrulefill"], 0

def generate_document(config):
    # Declare variables that will be used to generate the very first
    # section (document class and packages).
    document_class = "article"
    document_class_options = []
    packages = []

    # Add document class options that we can determine right away.
    font_size = config.get_enum("font-size", ["10", "11", "12"])
    document_class_options.append(font_size + "pt")

    # Add conditional packages.
    if config.get_boolean("fancy-math"):
        packages.append("amsmath")
        packages.append("amssymb")
    if not config.get_boolean("indent-paragraphs"):
        packages.append("parskip")

    # Make a variable where we will put the rest of the preamble.
    preamble_blocks = []

    # Make lists of end user defined variables and ifs to create.
    variables = set()
    ifs = set()
    macros = set()

    # Create ifs and macros that don't require anything special.
    if config.get_boolean("clearpage-option"):
        ifs.add("clearpage")
        macros.add("maybeclearpage")
    if config.get_boolean("problem-macro"):
        macros.add("problem")
    if config.get_boolean("solution-macro"):
        macros.add("solution")

    # Handle fancy margins.
    if config.get_boolean("fancy-marginals"):
        packages.append("fancyhdr")
        order = config.get_enum_list("marginal-position-order", unique=True)
        def handle_marginals(key_name, style_name):
            block = []
            for position, content in sort_by(
                    config.get_enum_enum_map(
                        key_name, MARGINAL_POSITIONS, MARGINALS),
                    order):
                macro = format_marginal(content, variables)
                block.append(r"  \{}{{{}}}".format(macro))
            if block:
                block.sort()
                block.insert(0, r"  \fancyhf{}")
                block.insert(
                    0, r"\fancypagestyle{{{}}}{" .format(style_name))
                block.append(r"}")
                preamble_blocks.append(block)
        page_styles_block = []
        handle_marginals("primary-marginals", "primary")
        page_styles_block.append(r"\pagestyle{primary}")
        if config.get_boolean("use-firstpage-marginals"):
            handle_marginals("firstpage-marginals", "first")
            page_styles_block.append(r"\thispagestyle{first}")
        else:
            config.ignored("firstpage-marginals",
                           "use-firstpage-marginals was set to false")
        preamble_blocks.append(page_styles_block)
    else:
        for key in "firstpage-marginals", "primary-marginals":
            config.ignored(key, "fancy-marginals was set to false")

    # Generate the block for page layout.
    if config.get_boolean("fancy-page-layout"):
        packages.append("geometry")
        margin = config.get_length("margin")
        page_layout_block = []
        page_layout_block.append(r"\geometry[margin={}]".format(margin))
        preamble_blocks.append(page_layout_block)
    else:
        config.ignored("margin", "fancy-page-layout was set to false")

    # Generate the block for list settings.
    if config.get_boolean("fancy-lists"):
        packages.append("enumitem")
        list_styles = config.get_enum_list(
            "list-number-style", LIST_STYLES.keys(),
        )
        list_block = []
        if isinstance(list_styles, list):
            for level, list_style in enumerate(list_styles, 1):
                if level > 4:
                    config.warn(
                        "Last {} elements of list-number-style were "
                        .format(len(list_style) - 4) + "ignored " +
                        "(only 4 are allowed)")
                    list_block.append(r"\setlist[enumerate,{}]{label={}}"
                                      .format(level, LIST_STYLES[list_style]))
            else:
                list_block.append(r"\setlist[enumerate]{{label={}}}"
                                  .format(LIST_STYLES[list_styles]))
        preamble_blocks.append(list_block)

    # Make variables for the document body.
    body_blocks = []

    # Add preamble.
    body_blocks.append([r"\begin{document}"])
    if config.get_boolean("use-firstpage-header"):
        header_block = []
        header_contents = config.get_enum_list("firstpage-header", MARGINALS)
        for i, content in enumerate(header_contents):
            macro = format_marginal(content, variables)
            if i != len(header_contents) - 1:
                header_block.append(r"  {} \\".format(macro))
            else:
                header_block.append(r"  {}".format(macro))
        if header_block:
            header_block.insert(0, r"\begin{flushright}")
            header_block.append(r"\end{flushright}")
            body_blocks.append(header_block)

    # Add problems.
    for i, problem in enumerate(config.get_string_list("problems")):
        problem_block = []
        if i != 0:
            if "maybeclearpage" in macros:
                problem_block.append(r"\maybeclearpage")
            elif config.get_boolean("clearpage"):
                problem_block.append(r"\clearpage")
        if "problem" in macros:
            problem_block.append(r"\problem{{{}}}".format(problem))
        else:
            problem_block.extend(format_problem(config, problem)[0])
        body_blocks.append(problem_block)
        if "solution" in macros:
            body_blocks.append(format_solution(config)[0])
        body_blocks.append([])

    # Finish up.
    body_blocks.append([r"\end{document}"])

    # Now that packages, variables, ifs, and macros have been
    # collected, we can make their blocks.
    aggregate_blocks = []

    # Make document-class and packages block.
    package_block = []
    document_class_decl = r"\documentclass"
    if document_class_options:
        document_class_decl += r"[{}]".format(",".join(document_class_options))
    document_class_decl += r"{{{}}}".format(document_class)
    package_block.append(document_class_decl)
    for package in packages:
        package_block.append(r"\usepackage{{{}}}".format(package))
    aggregate_blocks.append(package_block)

    # Make reusable list of sorted ifs.
    sorted_ifs = sort_by(ifs, config.get_enum_list("if-order", IFS))

    # Make the block for defining ifs.
    if_block = []
    for switch in sorted_ifs:
        if_block.append(r"\newif\if{}".format(switch))
    if if_block:
        aggregate_blocks.append(if_block)

    # Make the block for defining variables.
    variable_block = []
    for variable in sort_by(
            variables, config.get_enum_list("variable-order", VARIABLES)):
        value = config.get_string(variable)
        variable_block.append(r"\newcommand{{\{\}}}{{{}}}"
                              .format(variable, value))
    if variable_block:
        aggregate_blocks.append(variable_block)

    # Make the block for setting ifs.
    switch_block = []
    for switch in sorted_ifs:
        value = config.get_boolean(switch)
        value_str = "true" if value else "false"
        switch_block.append(r"\{}{}".format(switch, value_str))
    if switch_block:
        aggregate_blocks.append(switch_block)

    # Make the block for defining autogenerated macros.
    macro_block = []
    for macro in sort_by(macros, config.get_enum_list("macro-list", MACROS)):
        fn = globals()["format_" + macro]
        definition, num_args = fn(config, *MACRO_ARGS)
        line = r"\newcommand{{\{}}}".format(macro)
        if num_args >= 1:
            line += r"[{}]".format(num_args)
        line += r"{{{}}}".format(definition)
        macro_block.append(line)
    if macro_block:
        aggregate_blocks.append(macro_block)

    # Combine blocks.
    blocks = aggregate_blocks + preamble_blocks + body_blocks
    document_block = combine_blocks(*blocks)
    document = combine_block(document_block)

    # Print remaining warnings.
    config.warn_unused()

    return document
