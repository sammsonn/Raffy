import os
import glob
import openai
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader

openai.api_key = "API_KEY"
vectorstore_dict = {}

try:
    # Load all .docx files from the specified directory
    file_paths = glob.glob("../KnowledgeBases/*.docx")
    print(f"Loaded {len(file_paths)} file paths.")
except Exception as e:
    print("Error loading file paths: ", e)

for file_path in file_paths:
    try:
        # Load document from .docx file
        loader = DirectoryLoader(os.path.dirname(file_path), glob=os.path.basename(file_path))
        docs = loader.load()
        print(f"Loaded {len(docs)} documents from {file_path}.")
    except Exception as e:
        print(f"Error loading document from {file_path}: ", e)
        continue

    try:
        # Split document into chunks
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=200, chunk_overlap=100
        )
        doc_splits = text_splitter.split_documents(docs)
        print(f"Split {len(doc_splits)} documents from {file_path}.")
    except Exception as e:
        print(f"Error splitting document from {file_path}: ", e)
        continue

    try:
        # Add to vectorDB
        vectorstore = Chroma.from_documents(
            documents=doc_splits,
            collection_name=f"rag-chroma-{os.path.basename(file_path)}",
            embedding=OpenAIEmbeddings(openai_api_key=openai.api_key),
        )
        
        # hashmap de vectorstore
        vectorstore_dict[os.path.basename(file_path)] = vectorstore
        
        print(f"Created vectorDB for {file_path}.")
    except Exception as e:
        print(f"Error creating vectorDB for {file_path}:")
        continue
