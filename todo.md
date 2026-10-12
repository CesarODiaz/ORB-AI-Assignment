# Objective

This assignment including:

- LLM integration and prompt engineering
- Data extraction and structured output
- Conversation flow management
- Error handling and edge cases
- Code quality and testing
- System design and scalability considerations
- Optional RAG implementation

# Intelligent Conversational Agent

## Overview

Create a conversational AI system that simulates an intelligent agent for a fictional
business. The bot should conduct short interviews with customers to gather
information and provide appropriate responses. The agent function can be
customer support, scheduling agent, or any other function that requires obtaining
some information from the customer.

## Core Requirements

1. **Conversational Flow**
    - Implement a bot that can engage in natural conversation with users
    - Bot should collect specific information. For example, for a customer
    support agent, the agent would collect information about customer issues
    including: order number, problem category, problem description, and
    urgency level
    - Extract and validate this information into a structured format
    - Handle basic error cases and invalid inputs gracefully
    - Maintain conversation context throughout the interaction
2. **Data Extraction & Storage**
    - Store conversations and extracted data in a structured format (JSON)
    - Implement basic data validation for collected information
    - Generate a summary of the conversation with extracted key points
3. **Technical Requirements**
    - Use Python for implementation
    - Implement proper error handling
    - Use the LLM of your choice, considering the use case
    - Use the conversational AI platform/model of your choice for text
    transcription and TTS

## **Bonus Features (Optional)**

- Implement RAG using a provided knowledge base. For example, for a
customer support agent, knowledge of common customer issues
- Add sentiment analysis to detect customer frustration
- Implement multi-turn conversation memory
- Add support for multiple languages

## Deliverables

1. Source code in a Git repository
2. README with:
    - Setup instructions
    - System architecture overview
    - Explanation of key design decisions
    - Description of potential improvements
3. URL to demo video of sample conversations demonstrating the bot's capabilities
