"""
This module contains classes and functions to interact with the OpenAI API.

Classes:
    Agent: Manages communication with the OpenAI API and stores a history of messages.
    ColorAgent: A subclass of Agent that provides colored console output.

Functions:
    make_message: Constructs a message in the appropriate dictionary format.

Configuration:
    The OpenAI API key is expected to be set via environment variables. 

Example Usage:
    >>> from agent import Agent
    >>> my_agent = Agent(temperature=0.0)
    >>> my_agent.get_full_response("What is Python?")
    "Python is a popular high-level programming language known for..."
"""

from collections import deque
import os
import typing
import openai

from printer import COLORS, ColorPrinter

openai.api_key = os.getenv("OPENAI_API_KEY")


def make_message(
    role: typing.Literal["system", "user", "assistant"], content: str
) -> dict[str, str]:
    """
    Constructs a dictionary representing a message.

    The message is a dictionary with two key-value pairs:
    'role' indicating the sender's role and 'content' indicating the message text.

    Args:
        role (typing.Literal["system", "user", "assistant"]): The sender's role.
        content (str): The actual message content.

    Raises:
        ValueError: If the role is not one of "system", "user", or "assistant".

    Returns:
        dict[str, str]: A dictionary representing the message.
    """
    if role not in ("system", "user", "assistant"):
        raise ValueError(f"Invalid role: {role}")
    return {"role": role, "content": content}


class Agent:
    """
    Represents an agent that interacts with the OpenAI API.

    This agent maintains a message history for a continuous interaction
    with the OpenAI API.

    Attributes:
        _history (deque[dict[str, str]]): The message history with ChatGPT.
        _messages (list[dict[str, str]]): Permanent messages that precede user messages.
        _openai_kwargs (dict): Additional parameters for the OpenAI API call.

    Example:
        >>> agent = Agent(
                openai_model="gpt-4",
                max_tokens_per_call=3000,
                max_history=0,
                top_p=0.2,
            )
        >>> agent.get_full_response("Hi!")
        "Hi! How are you?"
    """

    def __init__(
        self,
        openai_model: str,
        max_tokens_per_call: int,
        max_history: int,
        **kwargs,
    ) -> None:
        """
        Initialize the Agent object.

        Args:
            openai_model (str): The OpenAI model to use.
            max_tokens_per_call (int, optional): Maximum tokens per API call.
            max_history (int, optional): Maximum messages in history.
            **kwargs: Additional keyword arguments for the OpenAI API,
            eg. top_p and temperature.
        """
        self._openai_model = openai_model
        self._max_tokens = max_tokens_per_call
        self._history: deque[dict[str, str]] = deque()
        self._max_history = max_history
        self._openai_kwargs = kwargs
        self._messages: list[dict[str, str]] = []

    def append_message(
        self,
        role: typing.Literal["system", "user", "assistant"],
        content: str,
        history: bool = True,
    ) -> None:
        """
        Add a new message to either the agent's history or permanent messages.

        Args:
            role (typing.Literal["system", "user", "assistant"]): Role of the message
            sender.
            content (str): Text content of the message.
            history (bool, optional): If True, add the message to the agent's history.
            If False, add to the agent's permanent messages. Defaults to True.
        """
        if history:
            self._history.append(make_message(role, content))
        else:
            self._messages.append(make_message(role, content))

    def generate_response(self, user_message: str = "") -> typing.Iterator[str]:
        """
        Sends the accumulated messages (permanent and history) to the OpenAI API and
        yields the assistant's response in an Iterator stream.

        If a user message is provided, it's added to the history before sending.
        The function ensures that the history
        doesn't exceed its set limit by removing older messages.

        Args:
            user_message (str, optional): The user's message to be sent to the API.
            Defaults to "".

        Yields:
            typing.Iterator[str]: The assistant's response from the OpenAI API.
        """
        while len(self._history) > self._max_history:
            self._history.popleft()

        if user_message:
            self._history.append(make_message("user", user_message))

        # Create a new completion with the current history and permanent messages.
        completion_stream = openai.ChatCompletion.create(  # type: ignore
            model=self._openai_model,
            max_tokens=self._max_tokens,
            messages=self._messages + list(self._history),
            stream=True,
            **self._openai_kwargs,
        )
        for chunk in completion_stream:
            response = chunk.choices[0]["delta"]  # type: ignore
            if "content" not in response:
                continue
            message = response.content  # type: ignore
            # If the assistant's response is a continuation of the previous message,
            # append it to the previous message instead of creating a new one.
            if self._history and self._history[-1]["role"] == "assistant":
                self._history[-1]["content"] += message
            else:
                self._history.append(make_message("assistant", message))

            yield message

    def get_full_response(self, user_message: str = "") -> str:
        """
        Sends the accumulated messages (permanent and history) to the OpenAI API and
        returns the assistant's full response.

        If a user message is provided, it's added to the history before sending.
        The function ensures that the history
        doesn't exceed its set limit by removing older messages.

        Args:
            user_message (str, optional): The user's message to be sent to the API.
            Defaults to "".

        Returns:
            str: The assistant's full response from the OpenAI API.
        """
        messages = self.generate_response(user_message)
        return "".join(messages)


class ColorAgent(Agent):
    """
    An Agent subclass providing colored console output.

    This agent behaves like the base Agent but provides color-coded console outputs to
    differentiate messages visually.

    Attributes:
        color (ColorPrinter): An instance of the ColorPrinter class for colored output.

    Example:
        >>> colored_agent = ColorAgent(
                name="Alice",
                color="BLUE",
                openai_model="gpt-4",
                max_tokens_per_call=3000,
                max_history=0,
                temperature=0.2,
            )
        >>> colored_agent.get_full_response("Tell me a joke.")
        "[BLUE] ### Alice ###"
        "[BLUE] Why did the AI go to school? To improve its learning rate!"
    """

    def __init__(
        self,
        name: str,
        color: str,
        openai_model: str,
        max_tokens_per_call: int,
        max_history: int,
        **kwargs,
    ) -> None:
        """
        Initialize the ColorAgent with a specified color.

        Args:
            name (str): Name of the agent for display purposes.
            color (str): Console output color.
            openai_model (str): The OpenAI model to use.
            max_tokens_per_call (int, optional): Maximum tokens per API call.
            max_history (int, optional): Maximum messages in history.
            **kwargs: Additional keyword arguments for the OpenAI API.

        Raises:
            ValueError: If the provided color is not supported.
        """
        super().__init__(
            openai_model,
            max_tokens_per_call=max_tokens_per_call,
            max_history=max_history,
            **kwargs,
        )
        self._name = name
        if color not in COLORS:
            raise ValueError(f"Agent '{name}' has an invalid color: {color}")
        self._color_printer = ColorPrinter(color)

    def generate_response(self, user_message: str = "") -> typing.Iterator[str]:
        """
        Sends messages to the OpenAI API, yields the response, and prints the response
        in the specified color.

        Args:
            user_message (str, optional): The user's message to the API. Defaults to "".

        Yields:
            str: Colored response from the OpenAI API.
        """
        self._color_printer(f"### {self._name} ###")
        for message in super().generate_response(user_message):
            self._color_printer(message, end="")
            yield message
        self._color_printer("\n\n")
