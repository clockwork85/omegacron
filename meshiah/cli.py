"""Console script for meshiah."""
import argparse
import sys


def main():
    """Console script for meshiah."""
    parser = argparse.ArgumentParser()
    parser.add_argument('_', nargs='*')
    args = parser.parse_args()

    print("Arguments: " + str(args._))
    print("Replace this message by putting your code into "
          "meshiah.cli.main")
    return 0


if __name__ == "__main__":
    main()
