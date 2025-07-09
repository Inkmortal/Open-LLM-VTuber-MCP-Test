"""Description: This file contains the implementation of the `AsyncLLM` class.
This class is responsible for handling asynchronous interaction with OpenAI API compatible
endpoints for language generation.
"""

from typing import AsyncIterator, List, Dict, Any, Union
from openai import (
    AsyncStream,
    AsyncOpenAI,
    APIError,
    APIConnectionError,
    RateLimitError,
)
from openai.types.chat import ChatCompletionChunk
from loguru import logger

from .stateless_llm_interface import StatelessLLMInterface


class AsyncLLM(StatelessLLMInterface):
    def __init__(
        self,
        model: str,
        base_url: str,
        llm_api_key: str = "z",
        organization_id: str = "z",
        project_id: str = "z",
        temperature: float = 1.0,
    ):
        """
        Initializes an instance of the `AsyncLLM` class.

        Parameters:
        - model (str): The model to be used for language generation.
        - base_url (str): The base URL for the OpenAI API.
        - organization_id (str, optional): The organization ID for the OpenAI API. Defaults to "z".
        - project_id (str, optional): The project ID for the OpenAI API. Defaults to "z".
        - llm_api_key (str, optional): The API key for the OpenAI API. Defaults to "z".
        - temperature (float, optional): What sampling temperature to use, between 0 and 2. Defaults to 1.0.
        """
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.client = AsyncOpenAI(
            base_url=base_url,
            organization=organization_id,
            project=project_id,
            api_key=llm_api_key,
        )

        logger.info(
            f"Initialized AsyncLLM with the parameters: {self.base_url}, {self.model}"
        )

    async def supports_function_calling(self) -> bool:
        """OpenAI-compatible endpoints typically support function calling"""
        return True

    async def chat_completion(
        self, messages: List[Dict[str, Any]], system: str = None, tools: List[Dict[str, Any]] = None
    ) -> AsyncIterator[Union[str, Dict]]:
        """
        Generates a chat completion using the OpenAI API asynchronously.

        Parameters:
        - messages (List[Dict[str, Any]]): The list of messages to send to the API.
        - system (str, optional): System prompt to use for this completion.
        - tools (List[Dict[str, Any]], optional): List of tools available for the LLM to use.

        Yields:
        - Union[str, Dict]: Either text content or tool call dictionaries.

        Raises:
        - APIConnectionError: When the server cannot be reached
        - RateLimitError: When a 429 status code is received
        - APIError: For other API-related errors
        """
        logger.debug(f"Messages: {messages}")
        stream = None
        try:
            # If system prompt is provided, add it to the messages
            messages_with_system = messages
            if system:
                messages_with_system = [
                    {"role": "system", "content": system},
                    *messages,
                ]

            # Build kwargs for the API call
            kwargs = {
                "messages": messages_with_system,
                "model": self.model,
                "stream": True,
                "temperature": self.temperature,
            }
            
            # Add tools if provided
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            
            stream: AsyncStream[
                ChatCompletionChunk
            ] = await self.client.chat.completions.create(**kwargs)
            
            # Tool call aggregator for streaming chunks
            tool_calls_aggregator = {}  # {index: {"id": ..., "name": ..., "arguments": ""}}
            
            async for chunk in stream:
                delta = chunk.choices[0].delta
                
                # Yield text content
                if delta.content:
                    yield delta.content
                
                # Aggregate tool call chunks
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    for tool_call_chunk in delta.tool_calls:
                        index = tool_call_chunk.index
                        
                        # Initialize aggregator for this index
                        if index not in tool_calls_aggregator:
                            tool_calls_aggregator[index] = {
                                "id": tool_call_chunk.id,
                                "name": "",
                                "arguments": ""
                            }
                        
                        # Accumulate name and arguments
                        if tool_call_chunk.function.name:
                            tool_calls_aggregator[index]["name"] += tool_call_chunk.function.name
                        if tool_call_chunk.function.arguments:
                            tool_calls_aggregator[index]["arguments"] += tool_call_chunk.function.arguments
            
            # After stream completes, yield complete tool calls
            for index, call_info in tool_calls_aggregator.items():
                if call_info["name"]:  # Only yield if we have a function name
                    # Generate ID if missing or empty
                    tool_id = call_info["id"]
                    if not tool_id:
                        tool_id = f"call_{index}_{call_info['name']}"
                        logger.debug(f"Generated tool call ID: {tool_id}")
                    
                    yield {
                        "type": "tool_call",
                        "id": tool_id,
                        "function": {
                            "name": call_info["name"],
                            "arguments": call_info["arguments"]
                        }
                    }

        except APIConnectionError as e:
            logger.error(
                f"Error calling the chat endpoint: Connection error. Failed to connect to the LLM API. \nCheck the configurations and the reachability of the LLM backend. \nSee the logs for details. \nTroubleshooting with documentation: https://open-llm-vtuber.github.io/docs/faq#%E9%81%87%E5%88%B0-error-calling-the-chat-endpoint-%E9%94%99%E8%AF%AF%E6%80%8E%E4%B9%88%E5%8A%9E \n{e.__cause__}"
            )
            yield "Error calling the chat endpoint: Connection error. Failed to connect to the LLM API. Check the configurations and the reachability of the LLM backend. See the logs for details. Troubleshooting with documentation: [https://open-llm-vtuber.github.io/docs/faq#%E9%81%87%E5%88%B0-error-calling-the-chat-endpoint-%E9%94%99%E8%AF%AF%E6%80%8E%E4%B9%88%E5%8A%9E]"

        except RateLimitError as e:
            logger.error(
                f"Error calling the chat endpoint: Rate limit exceeded: {e.response}"
            )
            yield "Error calling the chat endpoint: Rate limit exceeded. Please try again later. See the logs for details."

        except APIError as e:
            # Check if it's a tools-related error
            if tools and ("tools" in str(e).lower() or "function" in str(e).lower()):
                logger.warning(f"Provider doesn't support tools, falling back: {e}")
                # Recursive call without tools
                kwargs.pop("tools", None)
                kwargs.pop("tool_choice", None)
                stream = await self.client.chat.completions.create(**kwargs)
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                logger.error(f"LLM API: Error occurred: {e}")
                logger.info(f"Base URL: {self.base_url}")
                logger.info(f"Model: {self.model}")
                logger.info(f"Messages: {messages}")
                logger.info(f"temperature: {self.temperature}")
                yield "Error calling the chat endpoint: Error occurred while generating response. See the logs for details."

        finally:
            # make sure the stream is properly closed
            # so when interrupted, no more tokens will being generated.
            if stream:
                logger.debug("Chat completion finished.")
                await stream.close()
                logger.debug("Stream closed.")
