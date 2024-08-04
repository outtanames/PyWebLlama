import argparse
from src.pywebagent.agent import act

def main(args):
    return act(
        args.url,
        args.task,
        args.num_history,
        **args.kwargs
    )
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, type=str, help="URL to act on")
    parser.add_argument("--task", required=True, type=str, help="Task to perform")
    parser.add_argument("--num_history", required=False, type=int, help="How many historical actions to feed", default=0)
    parser.add_argument("--kwargs", required=False, type=str, help="Task arguments", default={})
    args = parser.parse_args()
    status, output = main(args)
    print("Status:", status)
    print("Output:", output)
