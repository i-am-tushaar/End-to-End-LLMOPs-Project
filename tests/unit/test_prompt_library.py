"""
Unit tests for prompt_library.py

Purpose:
- Verify that both prompts are created correctly.
- Verify that PROMPT_REGISTRY contains the expected entries.
- Check that prompts include the required placeholders and instructions.
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from multi_doc_chat.prompts.prompt_library import (
    contextualize_question_prompt,
    context_qa_prompt,
    PROMPT_REGISTRY,
)


# ---------------------------------------------------------
# 1. Test contextualization prompt creation
# ---------------------------------------------------------
def test_contextualize_prompt_is_chat_prompt_template():
    # The contextualization prompt should be a valid LangChain prompt.
    assert isinstance(contextualize_question_prompt, ChatPromptTemplate)


# ---------------------------------------------------------
# 2. Test question contextualization placeholders
# ---------------------------------------------------------
def test_contextualize_prompt_has_required_variables():
    # The prompt needs the current user input and conversation history.
    assert "input" in contextualize_question_prompt.input_variables
    assert "chat_history" in contextualize_question_prompt.input_variables


# ---------------------------------------------------------
# 3. Test contextualization prompt instructions
# ---------------------------------------------------------
def test_contextualize_prompt_contains_rewrite_instruction():
    # The system message should instruct the model to rewrite the query
    # as a standalone question without answering it.
    system_message = contextualize_question_prompt.messages[0]
    prompt_text = system_message.prompt.template

    assert "standalone question" in prompt_text
    assert "Do not provide an answer" in prompt_text


# ---------------------------------------------------------
# 4. Test question-answer prompt creation
# ---------------------------------------------------------
def test_context_qa_prompt_is_chat_prompt_template():
    # The question-answer prompt should also be a valid chat prompt.
    assert isinstance(context_qa_prompt, ChatPromptTemplate)


# ---------------------------------------------------------
# 5. Test question-answer prompt placeholders
# ---------------------------------------------------------
def test_context_qa_prompt_has_required_variables():
    # The answering prompt needs retrieved context, user input,
    # and the conversation history.
    assert "context" in context_qa_prompt.input_variables
    assert "input" in context_qa_prompt.input_variables
    assert "chat_history" in context_qa_prompt.input_variables


# ---------------------------------------------------------
# 6. Test question-answer prompt instructions
# ---------------------------------------------------------
def test_context_qa_prompt_contains_grounding_rules():
    # Answers must rely on retrieved context and stay concise.
    system_message = context_qa_prompt.messages[0]
    prompt_text = system_message.prompt.template

    assert "provided context" in prompt_text
    assert "I don't know." in prompt_text
    assert "three sentences" in prompt_text


# ---------------------------------------------------------
# 7. Test conversation history placeholders
# ---------------------------------------------------------
def test_both_prompts_use_messages_placeholder():
    # MessagesPlaceholder allows conversation history to be inserted
    # dynamically when the prompt is invoked.
    assert any(
        isinstance(message, MessagesPlaceholder)
        and message.variable_name == "chat_history"
        for message in contextualize_question_prompt.messages
    )

    assert any(
        isinstance(message, MessagesPlaceholder)
        and message.variable_name == "chat_history"
        for message in context_qa_prompt.messages
    )


# ---------------------------------------------------------
# 8. Test prompt registry entries
# ---------------------------------------------------------
def test_prompt_registry_contains_expected_keys():
    # Other modules use these keys to retrieve the correct prompts.
    assert "contextualize_question" in PROMPT_REGISTRY
    assert "context_qa" in PROMPT_REGISTRY


# ---------------------------------------------------------
# 9. Test registry maps keys to the correct prompts
# ---------------------------------------------------------
def test_prompt_registry_references_correct_prompts():
    # Confirm that each registry entry points to its intended prompt.
    assert (
        PROMPT_REGISTRY["contextualize_question"]
        is contextualize_question_prompt
    )
    assert PROMPT_REGISTRY["context_qa"] is context_qa_prompt


# ---------------------------------------------------------
# 10. Test that all registered prompts are valid templates
# ---------------------------------------------------------
def test_all_registered_prompts_are_chat_prompt_templates():
    # Every registered prompt should be a valid LangChain template.
    assert all(
        isinstance(prompt, ChatPromptTemplate)
        for prompt in PROMPT_REGISTRY.values()
    )
