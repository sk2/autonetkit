import sys

from autonetkit.workflow.workflow import BaseWorkflow


def main(filename):
    """

    @param filename:
    """
    workflow = BaseWorkflow()
    network_model = workflow.load(filename)
    workflow.run(network_model, target_platform="kathara")


if __name__ == '__main__':
    filename = sys.argv[1]
    main(filename)
