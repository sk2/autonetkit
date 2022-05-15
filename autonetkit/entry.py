from autonetkit.workflow.workflow import BaseWorkflow
import argparse


def parse_args() -> argparse.Namespace:
    """
    Standalone parser for for command arguments
    """
    # create an arg parser
    parser = argparse.ArgumentParser("autonetkit")
    parser.add_argument("-f", type=str, dest="filename")

    return parser.parse_args()


def main():
    """
    Entry point for autonetkit
    """

    args = parse_args()

    workflow = BaseWorkflow()
    network_model = workflow.load(args.filename)
    workflow.run(network_model, target_platform="kathara")


if __name__ == "__main__":
    """
    entrypoint for running directly
    """

    main()
