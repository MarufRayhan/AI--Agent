"""
Main module for the program.
"""

import json
import sys

import colorama

import config
import readinput


TASK = """
The user story is the following:
{}
"""


def fetch_validated_config(config_path: str) -> dict:
    """
    Load and validate the configuration from a specified file path.
    The function will print an error message and terminate the program if any issues
    are encountered.

    Parameters:
        config_path (str): The path to the configuration file.

    Returns:
        dict: The validated configuration dictionary.
    """
    try:
        print("Reading configuration file...")
        config_file = config.read_json(config_path)
        config.validate(config_file)
    except FileNotFoundError:
        print(f"Error: File '{config_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as err:
        print(f"Error: Invalid JSON format in '{config_path}': {err}")
        sys.exit(1)
    except ValueError as err:
        print(f"Error: {err}")
        sys.exit(1)
    except Exception as err:
        print(f"An error occurred while reading '{config_path}': {err}")
        sys.exit(1)
    print("Successfully read configuration file")
    return config_file






def fetch_task(input_path: str,mvp_path: str) -> str:
    """
    Load a task from a given file path or, if not provided, request it from the user.
    The function will print an error message and terminate the program if any issues
    are encountered.

    Parameters:
        input_path (str): The path to the input file containing the task.
        If empty or None, the task will be requested from the user.

    Returns:
        str: The loaded or inputted task.
    """
    if input_path:
        try:
            print("Reading input file...")
            task = config.read_file(input_path)
            print("Successfully read input file")
        except FileNotFoundError:
            print(f"Error: File '{input_path}' not found.")
            sys.exit(1)
        except Exception as err:
            print(f"An error occurred while reading '{input_path}': {err}")
            sys.exit(1)
    else:
        print(
            "Enter the User story. "
            f'When you\'re done, input "{colorama.Fore.BLUE}END{colorama.Fore.RESET}" '
            "or EOF (End Of File) to finish: "
        )
        mvp = config.read_file(mvp_path)
        task = readinput.read_lines()
        task += "\n\nMVP:\n" + mvp
        print("Successfully read task")
    print()
    return task

def main() -> None:
    args = config.parse_argument()

    # Load configuration file and create agents
    config_file = fetch_validated_config(args.config_file)
    agents = config.create_coloragents(config_file)
    agent_order = config_file["agent_order"]
    iterations = config_file.get("iterations", 1)

    # Fetch the initial user story
    user_story = fetch_task(args.input,args.mvp)

    # Iterate over each step for each agent
    for iteration in range(iterations):
        print(f"--- Phase {iteration + 1} ---")

        for agent_name in agent_order:
            # Find the agent configuration in the list
            agent_config = next((agent for agent in config_file["agents"] if agent["name"] == agent_name), None)
            if not agent_config:   
                continue

            task_info = agent_config["tasks"].get(str(iteration + 1))

            if task_info:
                if iteration == 0:
                    task = TASK.format(task_info) + "\n\nUser Story:\n" + user_story
                else:
                    task = TASK.format(task_info) + user_story
                print("-------------------------------")
                print(f"Assigning task to {agent_name}: {task_info}")
                agent = agents[agent_name]
                agent.append_message("user", task, False)
                response = agent.get_full_response()
                user_story = response
                # print(f"Response from {agent_name}: {response}")

                
main()


