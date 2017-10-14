**pset**: The simplest LaTeX problem-set templating engine that could
possibly work.

## Summary

_pset_ is a LaTeX generator. It reads extensive configuration data
from YAML or JSON files in parent directories, as well as from
command-line arguments and interactively from the user, and generates
a ready-to-use document template.

The primary use case of _pset_ is to typeset problem sets in a
university setting. It works equally well to quickly generate a
skeleton for personal use, or to create a template to send out to
others.

## Guiding principles

* Adhere to LaTeX best practices at all time.
* Value concision in output.
* Make configurable everything that can reasonably be configured.

## Origin

_pset_ was created as a replacement for [hmcpset], an antiquitated
one-size-fits-none LaTeX template in widespread use at Harvey Mudd
College. The advantages of _pset_ over hmcpset are as follows:

* _pset_ generates LaTeX code that is as minimal as possible, while
  still formatted consistently and readably. Furthermore, you can
  configure _pset_ to avoid the insertion of any particular package
  that you do not like. None of this is possible with hmcpset.

* You may customize the _pset_ template globally, per class, per
  assignment, and interactively using hierarchical configuration
  merging.

* _pset_ can be quickly updated to fix bugs, improve default behavior,
  and add new features -- all without breaking old documents.

* _pset_ follows best practices for its scripting language, Python,
  and its target language, LaTeX, while hmcpset is a mess of poorly
  formatted spaghetti code that produces LaTeX code of questionable
  quality and visual appeal.

[hmcpset]: https://www.math.hmc.edu/computing/support/tex/classes/hmcpset/
