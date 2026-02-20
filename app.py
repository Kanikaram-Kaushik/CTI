import streamlit as st
import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Embedding model (must match what was used in ingest.py)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Page configuration
st.set_page_config(
    page_title="CTI RAG Chatbot",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Cyber Threat Intelligence RAG Chatbot")
st.markdown("Ask questions about MITRE ATT&CK tactics, techniques, and mitigations.")

# Sidebar
with st.sidebar:
    st.header("Configuration")
    api_key_input = st.text_input(
        "OpenAI API Key (for answering questions)",
        type="password",
        value=os.getenv("OPENAI_API_KEY", "")
    )
    if api_key_input:
        os.environ["OPENAI_API_KEY"] = api_key_input

    st.divider()
    st.info("📦 Embeddings: local (all-MiniLM-L6-v2)\n\n🔍 Data Source: MITRE ATT&CK Enterprise")

# Check for API Key
if not os.getenv("OPENAI_API_KEY"):
    st.warning("⚠️ Please enter your OpenAI API Key in the sidebar to enable AI responses.")
    st.stop()


@st.cache_resource
def init_components():
    """Initialize the retriever and LLM using local embeddings."""
    fs_path = "faiss_index"

    if not os.path.exists(fs_path):
        return None, None

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vector_store = FAISS.load_local(fs_path, embeddings, allow_dangerous_deserialization=True)
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})

    llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
    return retriever, llm


retriever, llm = init_components()

if retriever is None:
    st.error(
        "❌ FAISS index not found. Please run the ingestion step first:\n\n"
        "```\npython ingest.py\n```"
    )
    st.stop()

# Build LCEL chain
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a Cyber Threat Intelligence analyst assistant. "
     "Use the following retrieved context from the MITRE ATT&CK knowledge base to answer the question accurately. "
     "If the context doesn't contain the answer, say so clearly and provide general guidance.\n\n"
     "Context:\n{context}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}"),
])


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def get_context(inputs):
    return format_docs(retriever.invoke(inputs["question"]))


def get_source_docs(question):
    return retriever.invoke(question)


chain = (
    RunnablePassthrough.assign(context=RunnableLambda(get_context))
    | prompt
    | llm
    | StrOutputParser()
)

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I am your CTI assistant powered by MITRE ATT&CK. Ask me about threats, techniques, or mitigations!"}
    ]

if "lc_chat_history" not in st.session_state:
    st.session_state.lc_chat_history = []

# Display Chat Messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input
if prompt_text := st.chat_input("Ask about a threat, technique, or mitigation..."):
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    with st.chat_message("user"):
        st.markdown(prompt_text)

    with st.chat_message("assistant"):
        with st.spinner("🔍 Analyzing threat intelligence..."):
            source_docs = get_source_docs(prompt_text)

            answer = chain.invoke({
                "question": prompt_text,
                "chat_history": st.session_state.lc_chat_history,
            })

            st.session_state.lc_chat_history.append(HumanMessage(content=prompt_text))
            st.session_state.lc_chat_history.append(AIMessage(content=answer))

            st.markdown(answer)

            with st.expander("📄 View Source Context"):
                for i, doc in enumerate(source_docs):
                    st.markdown(f"**Source {i+1}: {doc.metadata.get('name', 'Unknown')}**")
                    st.caption(f"Type: {doc.metadata.get('type', 'N/A')} | URL: {doc.metadata.get('url', 'N/A')}")
                    st.text(doc.page_content[:300] + "...")
                    st.divider()

            st.session_state.messages.append({"role": "assistant", "content": answer})
