def generate_macro_args():
    args = []
    for i in range(1, 10):
        args.append("#" + i)
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
        raise AssertionError

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
    font_size = config.get_enum("font-size", [10, 11, 12])
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

    return document
