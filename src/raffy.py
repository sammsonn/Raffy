import gradio as gr
import json
import inspect
from openai import AzureOpenAI
from classes import Agent, Response
from agents import agent_triaj, agent_persoana_fizica, agent_persoana_juridica
from knowledge import vectorstore_dict

# Configurare pentru Azure OpenAI
client = AzureOpenAI(
    azure_endpoint="ENDPOINT",
    api_key="API_KEY",
    api_version="2024-08-01-preview"
)

# Funții ajutătoare pentru gestionarea funcțiilor agentului
def function_to_schema(func) -> dict:
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        type(None): "null",
    }
    signature = inspect.signature(func)
    parameters = {
        param.name: {"type": type_map.get(param.annotation, "string")}
        for param in signature.parameters.values()
    }
    required = [
        param.name
        for param in signature.parameters.values()
        if param.default == inspect._empty
    ]

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": (func.__doc__ or "").strip(),
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required,
            },
        },
    }

def execute_tool_call(tool_call, tools, agent_name):
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    return tools[name](**args)  # apelează funcția corespunzătoare

def get_context(file_name, question):
    vectorstore = vectorstore_dict[file_name]
    retriever = vectorstore.as_retriever()
    sources = retriever.invoke(question)
    docs_text = "".join(d.page_content for d in sources)
    return docs_text

def run_full_turn(agent, messages):
    current_agent = agent
    context = ""
    
    # Dacă agentul nu este unul dintre cei trei agenți de bază
    if current_agent not in [agent_triaj, agent_persoana_fizica, agent_persoana_juridica]:
        context = get_context(current_agent.file_name, messages[-1]["content"])

    while True:
        tool_schemas = [function_to_schema(tool) for tool in current_agent.tools]
        tools = {tool.__name__: tool for tool in current_agent.tools}
        
        response = client.chat.completions.create(
            model=agent.model,
            messages=[{"role": "system", "content": current_agent.instructions + " Context: " + context}] + messages,
            tools=tool_schemas or None,
            temperature=0  # Adjusted temperature for more creative responses
        )
        
        message = response.choices[0].message
        messages.append(message)

        if message.content:
            return current_agent, message.content

        if not message.tool_calls:
            break

        for tool_call in message.tool_calls:
            result = execute_tool_call(tool_call, tools, current_agent.name)

            if isinstance(result, Agent):  # Schimb de agent
                current_agent = result
                result = f"Transfered to {current_agent.name}. Adopt persona immediately."

            result_message = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            }
            messages.append(result_message)

    return current_agent, Response(agent=current_agent, messages=messages)

# Funcția de chat pentru Gradio
current_agent = agent_triaj
messages = []

def chat_with_ai(user_input):
    global current_agent, messages
    messages.append({"role": "user", "content": user_input})
    current_agent, response = run_full_turn(current_agent, messages)
    messages.append({"role": "assistant", "content": response})
    return response

with gr.Blocks(css="""
    /* CSS to style the lateral borders and content */
    .chat-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 20px;
    }
    .chatbox {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        border-left: 5px solid yellow;
        border-right: 5px solid yellow;
        padding: 10px;
        width: 80%;  /* Adjust width as needed */
        max-width: 800px;
    }
    .banner {
        display: flex;
        align-items: center;
        background-color: yellow;
        padding: 10px;
        border-bottom: 3px solid black;
    }
    .banner h2 {
        color: black;
        margin-left: 10px;
        font-size: 32px;
    }
    .gradio-container {
        background-color: yellow;
        width: 100%;
    }
""") as chat_interface:

    gr.HTML(
        f"""
        <div class="banner">
            <h2 font-size>Raiffeisen Bank</h2>
        </div>
        """
    )
    

    gr.Markdown(f"""
    <h1 style='color: black;'>Hi! 👋 I'm Raffy, your personal banking assistant. How can I help you today?</h1>
    """)
    
    with gr.Column(elem_id="chat-container", visible=True):
        chat_history = gr.Chatbot(elem_id="chatbox", height=600)
        user_input = gr.Textbox(placeholder="Scrie un mesaj...")

        def respond(message, history):
            response = chat_with_ai(message)
            # Adding image to the left and text to the right
            history.append((message, '🤖 ' + response))
            return "", history

        user_input.submit(respond, inputs=[user_input, chat_history], outputs=[user_input, chat_history])

# Launching the Gradio interface
chat_interface.launch(share=True)
