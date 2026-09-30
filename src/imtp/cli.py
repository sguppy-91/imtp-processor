"""Command-line interface for the imtp package.

``imtp`` with no arguments launches the analyst-in-the-loop GUI
workflow (requires the ``[gui]`` extras). ``--help`` and ``--version``
work headless with only the core dependencies installed, because the
workflow (and therefore the GUI) is imported lazily.
"""
import argparse

from . import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="imtp",
        description="Isometric mid-thigh pull (IMTP) force-time analysis")
    parser.add_argument("--version", action="version",
                        version=f"imtp {__version__}")
    parser.parse_args(argv)

    # Default behaviour: the analyst-in-the-loop GUI workflow. Imported
    # lazily so the CLI works without the GUI dependencies installed.
    try:
        from .workflows import analyst
    except ImportError as e:
        parser.error(
            "the analyst GUI workflow needs the [gui] extras "
            f"(pip install -e '.[gui]'): {e}")
    analyst.run()


if __name__ == "__main__":
    main()
